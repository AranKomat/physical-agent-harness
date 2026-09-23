"""Adapters to existing NativeBindings and Journal without changing their schemas."""
from __future__ import annotations

import threading
import uuid
from dataclasses import replace

from physical_harness.execution.handoff.contracts import Phase, Regime, Route, integer, text


def wrap_native(native, hybrid, *, domain="behavior_sim"):
    """Inside the private native process, after constructing original NativeBindings.

    The policy Backend.execute must close over ORIGINAL native.run_skill, not this
    wrapper, to avoid recursion. observe is unchanged and must expose the SAME
    current legal observation as HybridExecutor.observe. Use only this bridge for
    actuator writes: Python callbacks are trusted, not an OS sandbox.
    """
    if domain not in {"fixture", "behavior_sim"} or hybrid.domain != domain:
        raise PermissionError("Hybrid domain mismatch; fixture bindings are not BEHAVIOR bindings")
    if getattr(native, "simulated", None) is not True:
        raise PermissionError("Hybrid V0 cannot wrap real hardware")
    if not getattr(native, "qualification_id", None):
        raise PermissionError("Original native bindings must be qualified")
    return replace(native, name=native.name + "+hybrid-v0", run_skill=hybrid.run_skill,
                   stop=hybrid.stop, qualification_id=native.qualification_id + "+hybrid-v0")


def journal_sink(journal, *, prefix="hybrid-v0"):
    """Reuse Journal.put with a distinct namespace for every sink incarnation."""
    text(prefix, maximum=400)
    session = uuid.uuid4().hex
    counter = 0
    lock = threading.Lock()

    def emit(kind, body):
        nonlocal counter
        with lock:
            counter += 1
            journal.put("hybrid", f"{prefix}:{session}:{counter}", {"type": kind, "payload": body})
    return emit


def ablation_routes(*, target: str, policy_instruction: str, total_steps=3224,
                    navigation_steps=300, staging_steps=300, retreat_steps=120,
                    max_wall_s=3600, max_policy_chunks=3224):
    """Declared A/B/C/D budgets, NOT authorization to run a campaign.

    Every route has the same TOTAL action ceiling, not the same policy exposure.
    No intermediate simulator resets; all starts must be ordinary task resets.
    A preserves one uninterrupted policy block; B adds navigation; C adds staging;
    D tests a guarded retreat. D requires safe_release_or_stable_payload evidence.
    """
    text(target)
    text(policy_instruction, maximum=4096)
    for n in (total_steps, navigation_steps, staging_steps, retreat_steps, max_policy_chunks):
        integer(n, minimum=1)
    if total_steps <= navigation_steps+staging_steps+retreat_steps:
        raise ValueError("Ablation must retain a positive learned-policy budget")

    def phase(name, regime, steps, instruction, extra=()):
        return Phase(name, regime, instruction, (target,), steps, max_wall_s,
                     max_policy_chunks if regime == Regime.POLICY else 0,
                     entry_checks=extra)

    nav = phase("navigate", Regime.NAVIGATE, navigation_steps, "Navigate to the observed staging region")
    stage = phase("stage", Regime.STAGE, staging_steps, "Move to the qualified policy handoff envelope")
    retreat = phase("retreat", Regime.RETREAT, retreat_steps, "Retract through the observed clear corridor",
                    ("safe_release_or_stable_payload",))
    result = {}
    for key, prefix, suffix in (("A", (), ()), ("B", (nav,), ()),
                                ("C", (nav, stage), ()), ("D", (nav, stage), (retreat,))):
        remaining = total_steps-sum(p.max_steps for p in prefix+suffix)
        learned = phase("learned", Regime.POLICY, remaining, policy_instruction)
        if key == "A":
            learned = replace(learned, policy_entry="ordinary_start")
        result[key] = Route(key, prefix+(learned,)+suffix)
    return result


def policy_exposure_diagnostic_routes(*, target: str, policy_instruction: str,
                                     policy_steps=384, navigation_steps=60, staging_steps=80,
                                     max_wall_s=600, max_policy_chunks=384):
    """Equal policy-action ceilings, intentionally unequal total-action ceilings.

    Freeze one condition per trial. This is not an executive action menu and is
    not a task-success comparison. Actual exposure can be censored by any gate,
    failure or wall deadline; report that instead of assuming the cap was used.
    """
    for value in (policy_steps, navigation_steps, staging_steps, max_policy_chunks):
        integer(value, minimum=1)
    # Reuse the established phase definitions and admission semantics, not a
    # second controller recipe. Retreat is omitted from these diagnostics.
    templates = ablation_routes(
        target=target, policy_instruction=policy_instruction,
        total_steps=policy_steps + navigation_steps + staging_steps + 1,
        navigation_steps=navigation_steps, staging_steps=staging_steps, retreat_steps=1,
        max_wall_s=max_wall_s, max_policy_chunks=max_policy_chunks,
    )
    return {
        key + "-short": Route(key + "-short", tuple(
            replace(phase, max_steps=policy_steps) if phase.regime == Regime.POLICY else phase
            for phase in templates[key].phases))
        for key in ("A", "B", "C")
    }
