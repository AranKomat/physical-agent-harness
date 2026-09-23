from dataclasses import replace

import pytest

from physical_harness.core.contracts import SkillReceipt
from physical_harness.core.jobs import JobManager
from physical_harness.execution.policy import MotorObservation
from physical_harness.execution.recovery import RecoveryService


def service():
    observation = [MotorObservation("ep", "o", 0, 0, 10)]
    jobs = JobManager(["bounded-l3", "motor"])

    def execute(preview):
        return SkillReceipt(
            preview.token, "fixture", "completed", 0, 0.1, metadata={"stop_acknowledged": True}
        )

    recovery = RecoveryService(
        "ep",
        jobs,
        lambda: observation[0],
        lambda e, o: e == "depth",
        lambda p: True,
        execute,
        recovery_allowed=lambda: True,
        qualified=True,
        clock=lambda: 10,
    )
    return recovery, observation, jobs


def test_preview_once_and_stale_observation_rejected():
    recovery, obs, jobs = service()
    p = recovery.preview("left_arm", (0.01, 0, 0), "depth")
    assert recovery.execute(p.token).outcome == "completed"
    assert not jobs.owners
    with pytest.raises(ValueError):
        recovery.execute(p.token)
    p = recovery.preview("left_arm", (0.01, 0, 0), "depth")
    obs[0] = replace(obs[0], observation_id="new")
    with pytest.raises(ValueError):
        recovery.execute(p.token)


def test_bounds_oracle_and_collision_fail_closed():
    recovery, _, _ = service()
    for delta, evidence in [((1, 0, 0), "depth"), ((0.01, 0, 0), "oracle")]:
        with pytest.raises(ValueError):
            recovery.preview("left_arm", delta, evidence)
    recovery.collision_check = lambda p: None
    with pytest.raises(ValueError):
        recovery.preview("left_arm", (0.01, 0, 0), "depth")


def test_motor_ownership_blocks_recovery():
    recovery, _, jobs = service()
    p = recovery.preview("left_arm", (0.01, 0, 0), "depth")
    jobs.start("motor-job", "motor", ["left_arm"], "o", 10, 20)
    with pytest.raises(ValueError):
        recovery.execute(p.token)
    assert jobs.owners["left_arm"] == "motor-job"


@pytest.mark.parametrize("invalidate", [False, True])
def test_acknowledged_late_or_invalidated_result_is_not_success(invalidate):
    recovery, _, jobs = service()
    preview = recovery.preview("left_arm", (0.01, 0, 0), "depth")
    original = recovery.execute_native

    def execute(p):
        if invalidate:
            jobs.invalidate_goal()
        else:
            recovery.clock = lambda: 13
        return original(p)

    recovery.execute_native = execute
    receipt = recovery.execute(preview.token)
    assert receipt.outcome == ("cancelled" if invalidate else "timeout")
    assert not jobs.owners
