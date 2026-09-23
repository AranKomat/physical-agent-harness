"""Adapters for existing Snapshot, NativeBindings, SkillReceipt and Journal.

Imports of the existing harness are lazy so geometry/proposal tools work in a
separate inference environment. This module does not modify the running campaign.
"""
from __future__ import annotations

import time
from dataclasses import replace

from physical_harness.core.actions import Basis, Primitive, integer, text
from physical_harness.execution.actions import ActionExecutor, StepReceipt
from physical_harness.planning.actions.compiler import Catalog


def basis_from_snapshot(snapshot, *, execution_epoch: int, robot_fingerprint: str,
                        calibration_fingerprint: str, evidence_ids: tuple[str, ...],
                        domain: str = "behavior_sim") -> Basis:
    from physical_harness.core.handoff import Snapshot
    if not isinstance(snapshot, Snapshot):
        raise ValueError("Use the existing validated Hybrid Snapshot")
    return Basis(snapshot.episode, snapshot.observation_id, snapshot.fingerprint,
                 snapshot.sim_time, snapshot.captured_wall, "local_map", snapshot.frame_epoch,
                 snapshot.geometry_revision, execution_epoch, robot_fingerprint,
                 calibration_fingerprint, evidence_ids, domain)


class CatalogMotor:
    """Publish one decision-time catalog beneath the existing HarnessRuntime.

    The existing executive selects from available_actions
    the compiler resolves
    parameters internally. The existing verifier/ledger remains downstream.
    Do not rebuild a catalog using final or future world state during replay.
    """
    name = "compiled-action-v1"

    def __init__(self, executor: ActionExecutor, *, max_wall_s: float = 60):
        self.executor, self.max_wall_s = executor, max_wall_s
        self.catalog = None

    def publish(self, catalog: Catalog):
        if not isinstance(catalog, Catalog):
            raise ValueError("Typed catalog required")
        self.catalog = catalog

    def actions(self, *, goal_id: str | None = None):
        from physical_harness.integrations.experiment.runner import Action
        if self.catalog is None:
            raise ValueError("Publish the exact decision-time catalog first")
        return [Action(a.id, f"{a.program.proposal.intent.verb.value} "
                             f"{a.program.proposal.intent.entity} / {a.program.proposal.intent.part}",
                       (a.program.proposal.intent.entity,), goal_id=goal_id,
                       skill_type="compiled_catalog", max_wall_s=self.max_wall_s,
                       max_action_steps=max(1, a.program.max_steps),
                       max_policy_chunks=max(1, sum(s.max_policy_chunks for s in a.program.steps)))
                for a in self.catalog.actions if a.eligible]

    def run_skill(self, request):
        from physical_harness.core.contracts import SkillReceipt, SkillRequest
        if not isinstance(request, SkillRequest) or self.catalog is None:
            raise ValueError("Published catalog and SkillRequest required")
        if (request.source_observation_id, request.execution_epoch) != (
            self.catalog.basis.observation_id, self.catalog.basis.execution_epoch
        ):
            raise PermissionError("Request is detached from the decision-time catalog")
        selected = request.metadata.get("action_id")
        action = next((a for a in self.catalog.actions if a.id == selected and a.eligible), None)
        if action is None:
            raise PermissionError("Action not in published catalog")
        if request.target_entities != (action.program.proposal.intent.entity,):
            raise PermissionError("Request altered the target binding")
        if sum(s.max_policy_chunks for s in action.program.steps) > request.max_policy_chunks:
            raise ValueError("Program exceeds outer chunk cap")
        result = self.executor.execute(self.catalog, {"catalog_id": self.catalog.id, "action_id": selected},
                                       max_steps=request.metadata["max_action_steps"],
                                       max_wall_s=request.max_wall_s)
        return SkillReceipt(request.skill_id, self.name, result.outcome,
                            result.before.sim_time, result.after.sim_time,
                            policy_calls=sum(r.policy_calls for r in result.receipts),
                            chunks_generated=sum(r.chunks_generated for r in result.receipts),
                            action_steps_executed=result.native_steps,
                            evidence_ids=tuple(dict.fromkeys(e for r in result.receipts for e in r.evidence_ids)),
                            observed_predicates=(),
                            metadata={"episode_id": result.before.episode,
                                      "execution_epoch": result.before.execution_epoch,
                                      "stop_acknowledged": result.stop_acknowledged})

    def stop(self):
        return self.executor.stop()

    def wrap_native(self, native):
        if native.simulated is not True or not native.qualification_id:
            raise PermissionError("Qualified simulator NativeBindings required")
        return replace(native, name=native.name+"+action-compiler", run_skill=self.run_skill,
                       stop=self.stop, qualification_id=native.qualification_id+"+action-compiler")


class FrozenPolicyPort:
    """A recipe-preserving adapter around an ORIGINAL non-owning native callback.

    `notify_classical_intervention` must be called by the native dispatcher for
    every nonpolicy motion. The reset callback must drain queued actions, history
    and in-flight work
    it must not reset the simulator. This wrapper never edits
    learned action vectors or chooses task-specific weights.
    """
    def __init__(self, *, identity, current_policy, reset_policy, run_skill, observe_basis,
                 native_skill_type: str, clock=time.monotonic):
        self.identity, self.current_policy = identity, current_policy
        self.reset_policy, self.native_run, self.observe_basis = reset_policy, run_skill, observe_basis
        self.native_skill_type = text(native_skill_type)
        self.generation = 0
        self.clock = clock
        self._needs_reset = True
        self._instruction = None

    def notify_classical_intervention(self):
        self._needs_reset = True

    def __call__(self, program, index, before, deadline, cancelled):
        from physical_harness.core.contracts import SkillRequest
        from physical_harness.core.handoff import ResetReceipt, ResetRequest
        if program.steps[index].kind != Primitive.POLICY:
            raise ValueError("FrozenPolicyPort handles policy steps only")
        if self.current_policy() != self.identity:
            raise PermissionError("Loaded checkpoint/codec/normalization/recipe changed")
        if self.identity.fingerprint != program.proposal.generator_revision:
            raise PermissionError("Candidate policy identity mismatch")
        if self.identity.action_dimensions != program.robot_dofs:
            raise PermissionError("Frozen policy action-space mismatch")
        instruction = program.proposal.parameters.instruction
        if self._needs_reset or self._instruction != instruction:
            self.generation += 1
            req = ResetRequest(before.episode, before.execution_epoch, self.generation,
                               instruction, before.observation_id, self.identity.fingerprint)
            ack = self.reset_policy(req, deadline)
            if not isinstance(ack, ResetReceipt):
                raise ValueError("Typed reset acknowledgement required")
            ack.require(req)
        if cancelled():
            raise InterruptedError("Policy call cancelled before dispatch")
        remaining = deadline-self.clock()
        if remaining <= 0:
            raise TimeoutError("Policy deadline exceeded before dispatch")
        step = program.steps[index]
        request = SkillRequest("compiled:"+program.fingerprint[:32]+":"+str(index),
                               self.native_skill_type, instruction,
                               target_entities=(program.proposal.intent.entity,),
                               max_wall_s=remaining, max_policy_chunks=step.max_policy_chunks,
                               source_observation_id=before.observation_id,
                               execution_epoch=before.execution_epoch,
                               metadata={"max_action_steps": step.max_steps,
                                         "policy_fingerprint": self.identity.fingerprint})
        raw = self.native_run(request)
        if self.current_policy() != self.identity or raw.skill_id != request.skill_id:
            raise PermissionError("Policy identity or receipt changed during execution")
        if raw.metadata.get("episode_id") != before.episode or raw.metadata.get("execution_epoch") != before.execution_epoch:
            raise PermissionError("Foreign policy receipt")
        after = self.observe_basis(deadline)
        if raw.sim_time_start != before.sim_time or raw.sim_time_end != after.sim_time:
            raise ValueError("Policy receipt/evidence clocks disagree")
        for n in (raw.policy_calls, raw.chunks_generated, raw.action_steps_executed):
            integer(n)
        self._needs_reset, self._instruction = False, instruction
        return StepReceipt(program.fingerprint, index, before, after, raw.outcome,
                           raw.action_steps_executed, raw.policy_calls, program.robot_dofs,
                           raw.metadata.get("stop_acknowledged") is True,
                           raw.evidence_ids or after.evidence_ids, chunks_generated=raw.chunks_generated)


class PrimitiveDispatcher:
    """Route primitives to operator-installed executors under ONE outer lease.

    Marks classical motion before invoking its handler so a later frozen-policy
    call drains obsolete inference state, including after a failed primitive.
    Inspect/measurement-only steps do not gratuitously reset temporal history.
    """
    def __init__(self, handlers: dict, *, frozen_policy: FrozenPolicyPort | None = None):
        if not handlers or not all(isinstance(k, Primitive) and callable(v)
                                   for k, v in handlers.items()):
            raise ValueError("Explicit typed primitive handlers required")
        self.handlers = dict(handlers)
        self.frozen_policy = frozen_policy
        if Primitive.POLICY in handlers and handlers[Primitive.POLICY] is not frozen_policy:
            raise ValueError("Policy handler must be the same reset-aware frozen policy port")

    def __call__(self, program, index, basis, deadline, cancelled):
        kind = program.steps[index].kind
        handler = self.handlers.get(kind)
        if handler is None:
            raise PermissionError("Primitive has no qualified native handler")
        if cancelled():
            raise InterruptedError("Cancelled before primitive dispatch")
        passive = {Primitive.INSPECT, Primitive.HOLD_CHECK, Primitive.RELEASE_CHECK}
        if kind != Primitive.POLICY and kind not in passive and self.frozen_policy is not None:
            self.frozen_policy.notify_classical_intervention()
        return handler(program, index, basis, deadline, cancelled)
