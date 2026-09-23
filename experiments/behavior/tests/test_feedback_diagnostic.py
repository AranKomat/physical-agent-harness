import json
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.behavior.base_hold import base_hold
from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.feedback_diagnostic import (
    JOINT_NAMES,
    PINNED_REVISION,
    FeedbackDiagnostic,
    run_feedback_hold,
)
from physical_harness.execution.handoff.classical import BodyTwist


class FakeSim:
    def __init__(self):
        self.currently_stepping = False
        self.currently_in_isaac_step = False
        self._in_sim_lifecycle = 0
        self._post_physics_step_callback = object()
        self.current_time_step_index = 0
        self.current_time = 0.
        self.calls = 0
        self.fail = False
        # Match the pinned dynamic subscription, not a captured bound method.
        self.subscription = lambda: self._on_post_physics_step()

    def get_physics_dt(self):
        return 1 / 120

    def _on_post_physics_step(self):
        self.calls += 1
        self.currently_stepping = self.currently_in_isaac_step = False
        if self.fail:
            raise LookupError("original callback")
        return "original result"

    def tick(self):
        self._in_sim_lifecycle = 1
        self.currently_stepping = self.currently_in_isaac_step = True
        self.current_time_step_index += 1
        self.current_time += self.get_physics_dt()
        try:
            return self.subscription()
        finally:
            self._in_sim_lifecycle = 0


class FakeRobot:
    def __init__(self, sim):
        self.sim = sim
        self.n_dof = 28
        # Deliberately non-contiguous/interleaved arm indices.
        order = [*range(10, 24, 2), *range(11, 24, 2), *range(6, 10), *range(24, 28)]
        self.joints = {name: SimpleNamespace(dof_indices=[index])
                       for name, index in zip(JOINT_NAMES, order)}
        self.q = np.arange(28, dtype=float)
        self.v = np.arange(28, dtype=float) / 100
        self.reads = []
        self.change_stamp = False

    def get_joint_positions(self):
        assert self.sim.calls > 0 and not self.sim.currently_stepping
        self.reads.append("q")
        return self.q

    def get_joint_velocities(self):
        self.reads.append("v")
        if self.change_stamp:
            self.sim.current_time_step_index += 1
        return self.v


def setup(**kwargs):
    sim = FakeSim()
    robot = FakeRobot(sim)
    log = FeedbackDiagnostic(sim, robot, source_revision=PINNED_REVISION, **kwargs)
    return sim, robot, log


def test_callback_order_named_indices_and_detached_output():
    sim, robot, log = setup()
    original = sim._on_post_physics_step
    with log:
        log.mark(control_sequence=384, phase="zero_base_hold")
        assert sim.tick() == "original result"
        frozen = json.loads(log.to_json())
        robot.q[:] = -1
        robot.v[:] = -2
        assert sim.tick() == "original result"
    result = json.loads(log.to_json())
    assert sim._on_post_physics_step == original
    assert "_on_post_physics_step" not in vars(sim)
    assert result["callback_removed"] and not result["installed"]
    assert robot.reads == ["q", "v", "q", "v"]
    row = result["rows"][0]
    assert row["joint_positions"] == [float(i) for i in result["dof_indices"]]
    assert row["native_joint_velocities"] == [i / 100 for i in result["dof_indices"]]
    assert min(result["dof_indices"]) == 6  # No virtual base positions.
    assert row["control_sequence"] == 384 and row["phase"] == "zero_base_hold"
    assert row["physics_step_index"] == 1 and row["sim_time_s"] == 1 / 120
    assert len(frozen["rows"]) == 1 and len(result["rows"]) == 2
    assert not result["native_getter_atomicity_proven"]
    log.close()
    sim.tick()
    assert sim.calls == 3 and len(json.loads(log.to_json())["rows"]) == 2


@pytest.mark.parametrize("limit", [2, 2000])
def test_cap_never_wraps_or_reads_more_feedback(limit):
    sim, robot, log = setup(max_rows=limit)
    with log:
        for _ in range(limit + 3):
            sim.tick()
    result = json.loads(log.to_json())
    assert len(result["rows"]) == limit and result["rows_dropped"] == 3
    assert result["callbacks_seen"] == sim.calls == limit + 3 and result["truncated"]
    assert robot.reads == ["q", "v"] * limit


@pytest.mark.parametrize("limit", [0, 2001, -1, True, 1.5])
def test_invalid_capacity(limit):
    with pytest.raises(ValueError):
        setup(max_rows=limit)


def test_revision_guard():
    with pytest.raises(ValueError, match="revision"):
        FeedbackDiagnostic(None, None, source_revision="other")


@pytest.mark.parametrize("failure", ["body", "original"])
def test_cleanup_preserves_exceptions(failure):
    sim, robot, log = setup()
    with pytest.raises(LookupError):
        with log:
            if failure == "body":
                raise LookupError("caller")
            sim.fail = True
            sim.tick()
    assert "_on_post_physics_step" not in vars(sim)
    assert not robot.reads
    assert json.loads(log.to_json())["callback_removed"]


@pytest.mark.parametrize("failure", ["nan", "stamp", "repeat"])
def test_bad_feedback_disables_logger_not_callback(failure):
    sim, robot, log = setup()
    with log:
        if failure == "nan":
            robot.q[10] = np.nan
        elif failure == "stamp":
            robot.change_stamp = True
        else:
            sim.tick()
            sim.current_time_step_index -= 1
            sim.current_time -= sim.get_physics_dt()
        assert sim.tick() == "original result"
        reads = len(robot.reads)
        assert sim.tick() == "original result"
        assert len(robot.reads) == reads
    result = json.loads(log.to_json())
    assert result["error"].startswith("feedback_read_failed:")
    assert result["rows_dropped"] == 2


def test_reject_existing_hook_and_nested_context():
    sim, robot, log = setup()
    with log:
        with pytest.raises(RuntimeError, match="Existing"):
            with FeedbackDiagnostic(sim, robot, source_revision=PINNED_REVISION):
                pass
    with pytest.raises(RuntimeError, match="one-shot"):
        with log:
            pass


def test_cleanup_does_not_clobber_replacement():
    sim, robot, log = setup()

    def replacement():
        return "other owner"

    with pytest.raises(RuntimeError, match="another owner"):
        with log:
            sim._on_post_physics_step = replacement
    assert sim._on_post_physics_step is replacement
    assert json.loads(log.to_json())["error"] == "cleanup_hook_ownership_conflict"


def test_cleanup_conflict_does_not_mask_body_exception():
    sim, robot, log = setup()
    with pytest.raises(ValueError, match="body") as caught:
        with log:
            sim._on_post_physics_step = lambda: None
            raise ValueError("body")
    assert "cleanup failed" in caught.value.__notes__[0]


def test_mapping_failure_leaves_callback_untouched():
    sim, robot, log = setup()
    robot.joints[JOINT_NAMES[-1]].dof_indices = [10]
    with pytest.raises(ValueError, match="mapping"):
        with log:
            pass
    assert "_on_post_physics_step" not in vars(sim)


def test_idle_guard_and_labels():
    sim, robot, log = setup()
    sim._in_sim_lifecycle = 1
    with pytest.raises(RuntimeError, match="during simulation"):
        log.__enter__()
    sim._in_sim_lifecycle = 0
    with log:
        for sequence, phase in ((True, "hold"), (-1, "hold"), (1, ""), (1, "x" * 81)):
            with pytest.raises(ValueError):
                log.mark(control_sequence=sequence, phase=phase)
        sim.tick()
    assert json.loads(log.to_json())["rows"][0]["control_sequence"] is None


def test_wrong_thread_callback_disables_sampling_without_touching_physics():
    sim, robot, log = setup()
    with log:
        thread = threading.Thread(target=sim.tick)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
    result = json.loads(log.to_json())
    assert sim.calls == 1 and not robot.reads
    assert result["rows"] == [] and result["error"] == "feedback_read_failed:RuntimeError"


def test_missing_subscription_refuses_installation():
    sim, robot, log = setup()
    sim._post_physics_step_callback = None
    with pytest.raises(RuntimeError, match="unavailable"):
        with log:
            pass
    assert "_on_post_physics_step" not in vars(sim)


def test_tensor_feedback_is_detached_and_copied_without_torch_import():
    class Tensor:
        def __init__(self, values):
            self.values = values

        def __getitem__(self, indices):
            return Tensor(self.values[indices])

        def detach(self):
            calls.append("detach")
            return self

        def clone(self):
            calls.append("clone")
            return Tensor(self.values.copy())

        def cpu(self):
            calls.append("cpu")
            return self

        def tolist(self):
            return self.values.tolist()

    calls = []
    sim, robot, log = setup()
    robot.q, robot.v = Tensor(robot.q), Tensor(robot.v)
    with log:
        sim.tick()
        robot.q.values[:] = 0
        robot.v.values[:] = 0
    row = json.loads(log.to_json())["rows"][0]
    assert row["joint_positions"][0] == 10 and row["native_joint_velocities"][0] == .1
    assert calls == ["detach", "clone", "cpu"] * 2


class HoldFixture:
    def __init__(self):
        self.sim = FakeSim()
        self.robot = FakeRobot(self.sim)
        self.p = np.zeros(61)
        self.p[3:10] = .1
        self.p[28:35] = -.1
        self.p[53:57] = .2
        self.p[[24, 25, 49, 50]] = .025
        self.initial = self.observation(384)
        self.commands, self.saved = [], []
        self.modify = lambda p, tick: None
        self.substeps = 4
        self.ended = False

    def observation(self, sequence):
        return Observation(stamp=Stamp(session="feedback-fixture", epoch=0, sequence=sequence),
                           observed_at=sequence / 30, rgb={}, depth={}, proprio=tuple(self.p))

    def step(self, command):
        self.commands.append(command)
        for _ in range(self.substeps):
            self.sim.tick()
        return self.ended

    def capture(self):
        self.modify(self.p, len(self.commands))
        return self.observation(384 + len(self.commands))

    def run(self, **overrides):
        args = dict(sim=self.sim, robot=self.robot, initial=self.initial,
                    gripper_ranges=((0., .05), (0., .05)), step=self.step,
                    capture=self.capture, save_feedback=self.saved.append)
        args.update(overrides)
        return run_feedback_hold(**args)


def test_hold_runs_all_60_constant_commands_with_hold_only_feedback():
    f = HoldFixture()
    f.sim.tick()  # Prior exposure is deliberately outside the logger context.
    final, report = f.run()
    assert final.stamp.sequence == 444 and report["passed"]
    assert report["actions_attempted"] == report["actions_completed"] == 60
    expected = base_hold(f.initial.proprio, BodyTwist(0, 0, 0),
                         gripper_ranges=((0., .05), (0., .05)))
    assert f.commands == [expected] * 60 and expected[:3] == (0., 0., 0.)
    assert report["final_consecutive_stopped"] == 60 and report["stop_acknowledged"]
    assert all(s["settled"] and s["stopped"] for s in report["samples"])
    assert all(s["joint_drift_rad"] == s["finger_drift_m"] == 0 for s in report["samples"])
    assert not report["motion_qualified"] and not report["strict_gates_overridden"]
    assert len(f.saved) == 1 and f.saved[0]["report"] == report
    feedback = f.saved[0]["feedback"]
    assert feedback["max_rows"] == 2000 and feedback["callback_removed"]
    assert len(feedback["rows"]) == 240 and feedback["rows"][0]["physics_step_index"] == 2
    assert [r["control_sequence"] for r in feedback["rows"]] == [
        seq for seq in range(385, 445) for _ in range(4)
    ]
    assert {r["phase"] for r in feedback["rows"]} == {"post_policy_zero_base_hold"}
    f.saved[0]["report"]["samples"].clear()
    assert len(report["samples"]) == 60


def test_moving_entry_can_issue_only_zero_base_brake_with_unchanged_poststep_guard():
    f = HoldFixture()
    p = list(f.initial.proprio)
    p[0], p[2] = .12, .2
    f.initial = f.initial.model_copy(update={"proprio": tuple(p)})
    _, report = f.run()
    assert report["passed"] and all(c[:3] == (0., 0., 0.) for c in f.commands)
    f = HoldFixture()
    f.initial = f.initial.model_copy(update={"proprio": tuple(p)})
    f.p[0] = .12
    _, report = f.run()
    assert len(f.commands) == 1 and "drift/speed guard" in report["error"]


@pytest.mark.parametrize("index,value", [(10, .031), (35, .031), (57, .031),
                                         (0, .0021), (2, .0051)])
def test_hold_keeps_unchanged_stop_checks(index, value):
    f = HoldFixture()
    f.p[index] = value
    final, report = f.run()
    assert len(f.commands) == 60 and final.stamp.sequence == 444
    assert not report["passed"] and not report["stop_acknowledged"]
    assert report["feedback_complete"] and not report["logger_error"]
    assert report["final_consecutive_stopped"] == 0
    assert all(not s["stopped"] for s in report["samples"])


@pytest.mark.parametrize("last_unstopped,expected", [(55, True), (56, False)])
def test_hold_requires_five_consecutive_final_samples(last_unstopped, expected):
    f = HoldFixture()

    def modify(p, tick):
        p[35] = .031 if tick == last_unstopped else 0

    f.modify = modify
    _, report = f.run()
    assert report["stop_acknowledged"] is expected and report["passed"] is expected
    assert report["final_consecutive_stopped"] == 60 - last_unstopped
    assert len(f.commands) == 60  # No early exit after the first five.


@pytest.mark.parametrize("index,delta", [(3, .0301), (24, .0061), (0, .0801), (2, .1501)])
def test_hold_aborts_drift_and_speed_guards_without_extra_actions(index, delta):
    f = HoldFixture()

    def modify(p, tick):
        p[index] += delta

    f.modify = modify
    final, report = f.run()
    assert final.stamp.sequence == 385 and len(f.commands) == 1
    assert "drift/speed guard" in report["error"]
    assert not report["passed"] and not report["stop_acknowledged"]
    assert len(report["samples"]) == len(f.saved) == 1
    assert f.saved[0]["feedback"]["callback_removed"]


@pytest.mark.parametrize("case", ["stale", "skip", "epoch", "time"])
def test_hold_rejects_nonfresh_capture_and_keeps_last_valid_observation(case):
    f = HoldFixture()

    def bad_capture():
        obs = f.capture()
        if case == "stale":
            return f.initial
        if case == "time":
            return obs.model_copy(update={"observed_at": f.initial.observed_at})
        stamp = obs.stamp.model_copy(update={"sequence": 386} if case == "skip" else {"epoch": 1})
        return obs.model_copy(update={"stamp": stamp})

    final, report = f.run(capture=bad_capture)
    assert final is f.initial and len(f.commands) == 1
    assert "fresh next-sequence" in report["error"] and not report["passed"]
    assert f.saved[0]["feedback"]["callback_removed"]


@pytest.mark.parametrize("case", ["step", "capture", "terminal", "interrupt"])
def test_hold_failure_always_exports_after_cleanup(case):
    f = HoldFixture()

    def bad_step(command):
        f.step(command)
        if case == "interrupt":
            raise KeyboardInterrupt()
        raise RuntimeError("step failed")

    def bad_capture():
        raise RuntimeError("capture failed")

    if case == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            f.run(step=bad_step)
    else:
        f.ended = case == "terminal"
        _, report = f.run(**({"step": bad_step} if case == "step" else
                            {"capture": bad_capture} if case == "capture" else {}))
        assert not report["passed"] and report["actions_attempted"] == 1
        assert report["actions_completed"] == (0 if case == "step" else 1)
    assert len(f.commands) == len(f.saved) == 1
    assert f.saved[0]["feedback"]["callback_removed"]
    assert not f.saved[0]["report"]["passed"]


@pytest.mark.parametrize("case", ["error", "missing", "overflow"])
def test_hold_exposes_feedback_failure_instead_of_claiming_success(case):
    f = HoldFixture()
    if case == "error":
        f.robot.q[10] = np.nan
    elif case == "missing":
        f.substeps = 0
    else:
        f.substeps = 2001
    _, report = f.run()
    assert len(f.commands) == 1 and not report["passed"] and not report["feedback_complete"]
    feedback = f.saved[0]["feedback"]
    assert feedback["callback_removed"] and len(feedback["rows"]) <= 2000
    if case == "error":
        assert report["logger_error"] == "feedback_read_failed:ValueError"
    elif case == "missing":
        assert "No physics feedback" in report["error"]
    else:
        assert feedback["truncated"] and feedback["rows_dropped"] == 1


def test_hold_save_failure_propagates_after_callback_removal():
    f = HoldFixture()

    def bad_save(packet):
        assert packet["feedback"]["callback_removed"]
        raise OSError("save failed")

    with pytest.raises(OSError, match="save failed"):
        f.run(save_feedback=bad_save)
    assert "_on_post_physics_step" not in vars(f.sim)


def test_hold_setup_failure_exports_and_does_not_step():
    f = HoldFixture()
    _, report = f.run(gripper_ranges=((0., 0.), (0., .05)))
    assert not f.commands and not report["passed"]
    assert len(f.saved) == 1 and f.saved[0]["feedback"] is None
