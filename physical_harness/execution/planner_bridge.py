from __future__ import annotations

from dataclasses import replace

from physical_harness.core.actions import Check, Primitive, Verb


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
