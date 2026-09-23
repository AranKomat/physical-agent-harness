"""Additive wiring, preserving the current native controller and existing authorities."""
from __future__ import annotations

from dataclasses import replace

from physical_harness.core.actions import Basis, Check, Primitive, Verb, digest
from physical_harness.core.discovery import DiscoveryRequest, RegionRef
from physical_harness.core.events import BoundaryEvent
from physical_harness.perception.keyframes import ViewSample


class DiscoveryCoordinator:
    """Main-thread owner for novelty -> async semantics -> historical inventory/events.

    No method commands motion, resets a policy, changes an IdentityLedger or
    mutates current metric world state. Main-thread poll is the only state writer.
    """
    def __init__(self, *, journal, keyframes, worker, inventory, executive_scheduler,
                 discovery_timeout_s=20.):
        from physical_harness.core.actions import number
        number(discovery_timeout_s, low=.01, high=300)
        self.journal, self.keyframes, self.worker = journal, keyframes, worker
        self.inventory, self.scheduler, self.timeout = inventory, executive_scheduler, discovery_timeout_s
        self.rooms_seen: set[str] = set()

    def observe(self, sample: ViewSample, *, now: float, task: str, task_revision: str,
                regions: tuple[RegionRef, ...] = (), room_id: str | None = None):
        reasons = self.keyframes.ingest(sample, now=now)
        if not reasons:
            return None
        frames = self.keyframes.select(sample.frame, now=now)
        selected_ids = {f.asset_id for f in frames}
        selected_regions = tuple(r for r in regions if r.frame_id in selected_ids)
        known, summary = self.inventory.known_summary(current=sample.frame.basis, now=now, task_revision=task_revision)
        first_room = room_id is not None and room_id not in self.rooms_seen
        request_id = digest([sample.frame.basis.episode, task_revision, [f.content_sha256 for f in frames],
                             sample.frame.basis.fingerprint, reasons])[:32]
        request = DiscoveryRequest(request_id, task, task_revision, sample.frame.basis, frames,
                                   selected_regions, known, self.inventory.revision, now, now+self.timeout,
                                   reasons, "room_initial" if first_room else "delta", known_summary_json=summary)
        accepted = self.worker.submit(request)
        self.journal.put("embodied_sampling", request_id, {"request_id": request_id, "accepted": accepted,
                         "buffer": self.keyframes.report(), "selected_frame_ids": list(selected_ids),
                         "region_count": len(selected_regions), "task_revision": task_revision})
        if accepted:
            self.keyframes.acknowledge_submission(frames)
            if first_room:
                self.rooms_seen.add(room_id)
            return request
        return None

    def poll(self, *, current: Basis, now: float, task_revision: str):
        if current.episode != self.journal.episode:
            raise PermissionError("Foreign discovery consumer")
        delivered = []
        for completion in self.worker.poll():
            result = completion.result
            if result is None:
                delivered.append({"request_id": completion.request_id, "error": completion.error_type})
                continue
            if result.request.current.sim_time > current.sim_time or result.completed_wall > now:
                raise PermissionError("Result isn't available at this consumer cutoff")
            item_ids = self.inventory.accept(result, received_wall=now, current_task_revision=task_revision)
            if result.request.task_revision == task_revision:
                for a in result.attention:
                    update = next(u for u in result.updates if u.local_id == a.local_id)
                    source = next(f for f in result.request.frames if f.asset_id == update.frame_id)
                    event = BoundaryEvent("discovery:"+result.request.id+":"+a.local_id,
                                          "relevant_discovery", source.basis, now, task_revision,
                                          source.basis.evidence_ids, a.significance)
                    self.scheduler.add(event, active_task_revision=task_revision)
            delivered.append({"request_id": completion.request_id, "items": item_ids,
                              "historical_only": True, "native_actions": 0})
        return tuple(delivered)


def focus_identity_view(identity, entity: str, current: Basis) -> dict:
    """Current geometry only through existing IdentityLedger.binding; no label-as-pose."""
    state = identity.state(entity)
    try:
        binding = identity.binding(entity, current)
        return {"entity": entity, "current_binding": binding, "current_geometry_available": True}
    except PermissionError:
        return {"entity": entity, "current_binding": None, "current_geometry_available": False,
                "remembered_semantics": state["canonical"], "visibility": state["visibility"],
                "conflicts": state["conflicts"], "association": state["association"],
                "notice": "Reobserve/reassociate before action; historical coordinates are not current."}


def attach_free_space_planner(driver, *, planner, request_factory, streamer):
    """Opt-in Driver.execute wrapper; current callbacks/gates/whole-robot owner retained.

    Only STAGE/RETRACT MOVE_EEF are routed to the new planner. No grasp/contact
    phase is silently reinterpreted as free-space. request_factory must bind the
    exact native robot, fixed holds, scene and current tool-frame transform.
    """
    original = driver.execute

    def execute(program, index, basis, deadline, cancelled):
        step = program.steps[index]
        if program.proposal.intent.verb not in {Verb.STAGE, Verb.RETRACT} or step.kind != Primitive.MOVE_EEF:
            return original(program, index, basis, deadline, cancelled)
        needed = {"embodied_planner_configuration", "embodied_planner_full_scene",
                  "embodied_named_joint_holds", "embodied_planner_timebase"}
        if not needed <= set(program.required_checks):
            raise PermissionError("Planner execution requires explicit new native qualification checks")
        request = request_factory(program, index, basis, deadline)
        basis.require_same(request.basis)
        if request.target != step.pose:
            raise PermissionError("Planner target differs from reviewed program")
        trajectory = planner.plan(request, deadline=deadline)
        return streamer.run(program, index, basis, request, trajectory, deadline, cancelled)

    return replace(driver, execute=execute)


def with_planner_requirements(program):
    extra = ("embodied_planner_configuration", "embodied_planner_full_scene",
             "embodied_named_joint_holds", "embodied_planner_timebase")
    return replace(program, required_checks=tuple(dict.fromkeys(program.required_checks+extra)),
                   recipe=program.recipe+"+classical-planner-v3")


def enforce_embodied_checks(driver, checks: dict):
    """Retain old review then require every embodied_* check per native step."""
    from physical_harness.execution.actions import StepReview
    original = driver.review_step
    if not all(isinstance(k,str) and callable(v) for k,v in checks.items()):
        raise ValueError("Named native review callbacks required")

    def review(program, index, basis, deadline):
        old = original(program, index, basis, deadline)
        if not isinstance(old, StepReview):
            raise ValueError("Existing per-step review required")
        old.require(program, index, basis)
        result = {c.name:c for c in old.checks}
        for name in program.required_checks:
            if not name.startswith("embodied_"):
                continue
            fn = checks.get(name)
            c = fn(program, index, basis, deadline) if fn else Check(name, None, basis.evidence_ids, "Unqualified native V3 check")
            if not isinstance(c, Check) or c.name != name or c.passed is not True:
                raise PermissionError("New native check is not established: "+name)
            result[name] = c
        return StepReview(program.fingerprint, index, basis.fingerprint, tuple(result.values()))
    return replace(driver, review_step=review)
