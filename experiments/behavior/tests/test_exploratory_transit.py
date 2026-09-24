import hashlib
import io
import time
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.behavior import exploratory_transit as transit
from experiments.behavior.contracts import Evidence, Observation, Stamp
from experiments.behavior.grounding_manifest import online_identity

from .test_feedback_diagnostic import FakeRobot, FakeSim


class Driver:
    def __init__(self, monkeypatch, tmp_path):
        self.sim = FakeSim()
        self.robot = FakeRobot(self.sim)
        self.sequence = 768
        self.p = np.zeros(61)
        self.p[[24, 25, 49, 50]] = .025
        self.commands, self.saved = [], []
        self.path = tmp_path
        self.phase = None
        self.moving = 0
        self.capture_count = 0
        self.on_step = lambda: None
        self.on_capture = lambda: None
        self.on_pair = lambda: None
        self.target_offset = 0.
        self.target_fail = False
        self.capture_fail = False
        self.fit_fail = False
        self.terminate = False
        self.distance = .001
        self.yaw = 0.
        monkeypatch.setattr(transit, "RobotSelfCheck", lambda _: object())
        monkeypatch.setattr(transit, "_frame", self.frame)
        monkeypatch.setattr(transit, "_target", self.target)
        monkeypatch.setattr(transit, "point_to_plane", self.icp)
        self.initial = self.capture()

    def capture(self):
        self.capture_count += 1
        self.on_capture()
        if self.capture_fail:
            raise RuntimeError("capture failed")
        stamp = Stamp(session="probe", epoch=0, sequence=self.sequence)
        now = time.monotonic()
        refs = {kind: {"head": Evidence(id=kind+str(self.sequence), stamp=stamp,
                observed_at=now, source=kind, uri="unused")} for kind in ("rgb", "depth")}
        self.obs = Observation(stamp=stamp, observed_at=now, proprio=tuple(self.p), **refs)
        return self.obs

    def frame(self, obs, row, store, fk):
        return dict(obs=obs, k=np.eye(3), depth=np.ones((10, 10)), extrinsic=np.eye(4))

    def target(self, frame, row, output):
        if self.target_fail:
            raise ValueError("Target lost or ambiguous")
        return np.array([1-self.moving*self.distance+self.target_offset, 0, 1.])

    def icp(self, *args):
        self.on_pair()
        t = np.eye(4)
        if self.phase == "move":
            t[0, 3] = -self.distance
            c, s = np.cos(self.yaw), np.sin(self.yaw)
            t[:2, :2] = [[c, -s], [s, c]]
        return not self.fit_fail, t, np.eye(6)

    def step(self, command):
        self.commands.append(command)
        self.phase = "move" if np.linalg.norm(command[:2]) else "hold"
        if self.phase == "move":
            self.moving += 1
        self.on_step()
        for _ in range(4):
            self.sim.tick()
        self.sequence += 1
        return self.terminate

    def run(self, **overrides):
        args = dict(sim=self.sim, robot=self.robot, store=None,
                    gripper_ranges=((0., .05), (0., .05)), step=self.step,
                    capture=self.capture, latest_row=lambda: {}, output=self.path,
                    save_probe=self.saved.append, robot_assets=self.path)
        args.update(overrides)
        return transit.run_exploratory_transit(self.initial, **args)

    @property
    def report(self):
        return self.saved[-1]["report"]

    def clean(self):
        assert "_on_post_physics_step" not in vars(self.sim)
        assert self.saved[-1]["feedback"]["callback_removed"]
        assert self.report["actions_attempted"] == len(self.commands)
        assert len(self.report["commands"]) == len(self.commands)


def test_sam_target_route_retains_probe_limits_and_journals(monkeypatch, tmp_path):
    from experiments.behavior.sam_transit_target import SAMTransitTarget

    d = Driver(monkeypatch, tmp_path)
    target = SAMTransitTarget(tmp_path, session="probe", epoch=0, generation=0, tracker_id=0)

    def sample(self, frame, row, output):
        point = d.target(frame, row, output)
        self.receipts.append({"motion_authorized": False, "surface_median_base_m": point.tolist()})
        return point

    monkeypatch.setattr(SAMTransitTarget, "__call__", sample)
    monkeypatch.setattr(transit, "_target", lambda *args: pytest.fail("Legacy target used"))
    d.run(sam_target=target)
    d.clean()
    assert d.report["passed"] and d.moving == 80
    assert not d.report["strict_gate_passed"]
    assert any("sam_target_proposal" in r for r in d.report["samples"])


def test_arbitrary_target_callback_rejected(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="source-bound"):
        d.run(sam_target=lambda *args: np.ones(3))
    assert not d.commands


def test_one_segment_frozen_joints_stop_and_fresh_final(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    final = d.run()
    d.clean()
    assert d.report["passed"] and d.report["experimental_stop_observed"]
    assert d.report["feedback_complete"]
    feedback = d.saved[-1]["feedback"]
    assert feedback["callback_removed"] and not feedback["installed"]
    assert not feedback["error"] and not feedback["truncated"] and feedback["rows_dropped"] == 0
    assert len(feedback["rows"]) == 4*d.report["actions_completed"]
    assert not d.report["strict_gate_passed"] and d.report["clearance"] == "unknown"
    assert d.moving == 80 and len(d.commands) == 92
    assert d.report["commanded_integral_m"] == pytest.approx(.08)
    assert d.report["measured_path_m"] == pytest.approx(.08)
    pose = np.asarray(d.report["entry_base_from_current"])
    assert pose[:3, 3] == pytest.approx([.08, 0, 0])
    assert np.allclose(pose[:3, :3], np.eye(3))
    transforms = [r["previous_base_from_current"] for r in d.report["samples"]
                  if "previous_base_from_current" in r]
    assert len(transforms) == d.report["actions_completed"]
    assert final.stamp.sequence == d.sequence and d.capture_count == len(d.commands)+3
    moving = [i for i, c in enumerate(d.commands) if c[0]]
    assert moving == list(range(6, 86))
    assert all(c[2] == 0 and c[3:] == d.commands[0][3:] for c in d.commands)
    assert all(np.linalg.norm(c[:2]) * .75 <= .03 for c in d.commands)
    assert all(r["raw_proprio_settled"] for r in d.report["samples"])


@pytest.mark.parametrize("failure", ["target", "capture", "icp", "drift", "speed", "switch"])
def test_failures_never_resume_drive_and_brake(monkeypatch, tmp_path, failure):
    d = Driver(monkeypatch, tmp_path)

    def trigger():
        if d.moving == 1:
            if failure == "target":
                d.target_fail = True
            elif failure == "capture":
                d.capture_fail = True
            elif failure == "icp":
                d.fit_fail = True
            elif failure == "drift":
                d.p[3] = .031
            elif failure == "speed":
                d.p[2] = .151
            else:
                d.target_offset = .2

    d.on_step = trigger
    d.run()
    d.clean()
    assert not d.report["passed"] and d.moving == 1
    assert 1 <= d.report["brake_attempts"] <= 60
    assert all(c[:3] == (0., 0., 0.) for c in d.commands[7:])
    if failure in ("capture", "icp"):
        assert d.report["brake_attempts"] == 60
        assert not d.report["measured_path_complete"]
        assert all(r.get("blind_zero_only") for r in d.report["commands"][7:])


def test_terminal_episode_no_more_steps(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    d.terminate = True
    d.run()
    d.clean()
    assert len(d.commands) == 1 and d.report["brake_attempts"] == 0
    assert d.report["episode_ended"]


@pytest.mark.parametrize("distance,yaw,reason", [(.003, 0, "rate/rotation"),
                                                (.001, .006, "rate/rotation"),
                                                (.101, 0, "hard abort")])
def test_drive_tracking_bounds(monkeypatch, tmp_path, distance, yaw, reason):
    d = Driver(monkeypatch, tmp_path)
    d.distance, d.yaw = distance, yaw
    d.run()
    d.clean()
    assert reason in d.report["error"] and d.moving == 1


def test_measured_budget_stops_before_command_budget(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    d.distance = .002
    d.run()
    assert d.report["passed"] and d.moving == 40
    assert d.report["commanded_integral_m"] == pytest.approx(.04)


def test_prehold_transient_does_not_apply_drive_depth_guard(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    original = d.icp
    count = 0

    def transient(*args):
        nonlocal count
        count += 1
        if count == 1:
            t = np.eye(4)
            yaw = .263160 / 30
            c, s = np.cos(yaw), np.sin(yaw)
            t[:2, :2] = [[c, -s], [s, c]]
            t[0, 3] = .050731 / 30
            return True, t, np.eye(6)
        return original(*args)

    monkeypatch.setattr(transit, "point_to_plane", transient)
    d.run()
    assert d.report["passed"] and d.report["prehold_experimental_stop"]


@pytest.mark.parametrize("kind", ["step", "interrupt", "save"])
def test_exception_cleanup_and_uncertain_sequences(monkeypatch, tmp_path, kind):
    d = Driver(monkeypatch, tmp_path)
    once = False

    def fail():
        nonlocal once
        if d.phase == "move" and not once:
            once = True
            if kind == "interrupt":
                raise KeyboardInterrupt()
            raise RuntimeError("uncertain native step")

    if kind == "save":
        def save(packet):
            if packet["feedback"] is None:
                return
            assert "_on_post_physics_step" not in vars(d.sim)
            raise OSError("save")
        with pytest.raises(OSError):
            d.run(save_probe=save)
        return
    d.on_step = fail
    if kind == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            d.run()
        assert d.report["brake_attempts"] == 1
    else:
        d.run()
        assert d.report["brake_attempts"] == 1
    d.clean()
    assert d.moving == 1 and not d.report["passed"]
    assert not d.report["feedback_complete"]
    assert all(r["post_sequence"] is None for r in d.report["commands"][6:])


def test_stale_command_cap_and_work_timeout(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    monkeypatch.setattr(transit, "CAPTURE_TO_COMMAND_S", 0)
    d.run()
    assert d.moving == 0 and "wall budget" in d.report["error"]
    assert d.report["commanded_integral_m"] == 0
    d.clean()


def test_physics_joint_window_uses_interval_max_not_net_displacement():
    rows = [dict(phase="hold", physics_step_index=i, sim_time_s=i/120,
                 joint_positions=[0.]*22) for i in range(21)]
    log = SimpleNamespace(_rows=rows, _error=None, _dropped=0)
    assert transit._joint_window(log, "hold")["joint_max_rad_s"] == 0
    rows[10]["joint_positions"][0] = .001
    assert transit._joint_window(log, "hold")["joint_max_rad_s"] == pytest.approx(.12)
    rows[10]["phase"] = "move"
    assert transit._joint_window(log, "hold") is None


@pytest.mark.parametrize("case", ["valid", "omitted", "ambiguous", "stale", "content", "delivery"])
def test_real_target_selection_binding(monkeypatch, tmp_path, case):
    d = Driver(monkeypatch, tmp_path)
    # Driver patches _target only for state-machine tests; recover real function.
    target = REAL_TARGET
    obs = d.initial
    mask = np.ones((10, 10), dtype=bool)
    data = io.BytesIO()
    np.save(data, mask, allow_pickle=False)
    digest = hashlib.sha256(data.getvalue()).hexdigest()
    root = tmp_path / "grounding_masks"
    root.mkdir()
    (root / (digest+".npy")).write_bytes(data.getvalue())
    point = [4.5, 4.5, 1.]
    candidate = dict(label="a radio", surface_median_camera_m=point,
                     surface_median_base_m=point,
                     derived_mask=dict(uri=digest+".npy", sha256=digest,
                                       stamp=obs.stamp.model_dump(), rgb_evidence_id=obs.rgb["head"].id))
    g = dict(identity=online_identity(), stamp=obs.stamp.model_dump(),
             rgb_evidence_id=obs.rgb["head"].id, depth_evidence_id=obs.depth["head"].id,
             motion_authorized=False, delivery="synchronous_before_next_native_action",
             omitted_target_count=0, candidates=[candidate])
    if case == "omitted":
        g["omitted_target_count"] = 1
    elif case == "ambiguous":
        g["candidates"].append(candidate)
    elif case == "stale":
        g["depth_evidence_id"] = "old"
    elif case == "content":
        (root / (digest+".npy")).write_bytes(b"corrupt")
    elif case == "delivery":
        g["delivery"] = "offline"
    frame = d.frame(obs, {}, None, None)
    if case == "valid":
        assert np.allclose(target(frame, {"target_grounding": g}, tmp_path), point)
    else:
        with pytest.raises(ValueError):
            target(frame, {"target_grounding": g}, tmp_path)


REAL_TARGET = transit._target


@pytest.mark.parametrize("failure", ["assets", "target", "capture"])
def test_preflight_failure_never_steps(monkeypatch, tmp_path, failure):
    d = Driver(monkeypatch, tmp_path)
    if failure == "assets":
        def fail(_):
            raise ValueError("assets")
        monkeypatch.setattr(transit, "RobotSelfCheck", fail)
    elif failure == "target":
        d.target_fail = True
    else:
        d.capture_fail = True
    d.run()
    assert not d.commands and d.report["brake_attempts"] == 0
    assert not d.report["passed"]
    assert "_on_post_physics_step" not in vars(d.sim)


def test_interim_receipt_precedes_native_command(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)

    def check():
        packet = d.saved[-1]
        assert packet["feedback"] is None
        receipt = packet["report"]["commands"][-1]
        assert receipt["command"] == list(d.commands[-1])
        assert not receipt["completed"] and receipt["post_sequence"] is None

    d.on_step = check
    d.run()
    d.clean()
    assert d.report["passed"]
    assert len(d.saved) == 2*len(d.commands)+1
    for record in d.report["commands"]:
        assert record["post_sequence"] == record["pre_sequence"]+1
        assert record["native_physics_after"] == record["native_physics_before"]+4


def test_joint_nonstop_has_bounded_prehold_and_brake(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)

    def moving_joint():
        d.robot.q[10] += .002

    d.on_step = moving_joint
    d.run()
    d.clean()
    assert not d.report["passed"] and d.moving == 0
    assert len(d.commands) == 120 and d.report["brake_attempts"] == 60


def test_work_timeout_reserves_brake_budget(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    expired = False

    def expire():
        nonlocal expired
        if d.moving == 1 and not expired:
            expired = True
            # Change the monotonic offset once; native observation timestamps
            # follow the same patched clock. Braking has its separate deadline.
            clock = time.monotonic
            monkeypatch.setattr(transit.time, "monotonic", lambda: clock()+601)

    d.on_step = expire
    d.run()
    d.clean()
    assert not d.report["passed"] and d.moving == 1
    assert d.report["brake_attempts"] > 0


def test_cleanup_failure_keeps_feedback(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    original = transit.FeedbackDiagnostic.close

    def close(log):
        original(log)
        raise RuntimeError("cleanup diagnostic")

    monkeypatch.setattr(transit.FeedbackDiagnostic, "close", close)
    d.run()
    assert not d.report["passed"] and "cleanup_error" in d.report
    assert d.saved[-1]["feedback"]["rows"]
    assert "_on_post_physics_step" not in vars(d.sim)


def test_slow_receipt_cannot_send_stale_nonzero_command(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    clock = time.monotonic
    offset = 0.
    delayed = False
    monkeypatch.setattr(transit.time, "monotonic", lambda: clock()+offset)

    def save(packet):
        nonlocal offset, delayed
        d.saved.append(packet)
        commands = packet["report"]["commands"]
        if (not delayed and packet["feedback"] is None and commands
                and commands[-1]["phase"] == "move" and not commands[-1]["completed"]):
            offset += transit.CAPTURE_TO_COMMAND_S + 1
            delayed = True

    d.run(save_probe=save)
    assert delayed
    assert d.moving == 0, "Recheck freshness after pre-step save and before native nonzero command"
    assert not d.report["passed"]
    assert "_on_post_physics_step" not in vars(d.sim)


@pytest.mark.parametrize("failure", ["missing", "read_error", "truncated"])
def test_incomplete_real_feedback_cannot_pass(monkeypatch, tmp_path, failure):
    d = Driver(monkeypatch, tmp_path)
    if failure == "missing":
        monkeypatch.setattr(transit.FeedbackDiagnostic, "_capture", lambda _: None)
    elif failure == "read_error":
        d.robot.q[10] = np.nan
    else:
        original = transit.FeedbackDiagnostic.__init__

        def small_log(log, *args, **kwargs):
            kwargs["max_rows"] = 2
            original(log, *args, **kwargs)

        monkeypatch.setattr(transit.FeedbackDiagnostic, "__init__", small_log)
    d.run()
    d.clean()
    assert d.moving == 0
    assert not d.report["passed"] and not d.report["feedback_complete"]
    feedback = d.saved[-1]["feedback"]
    if failure == "missing":
        assert feedback["rows"] == []
    elif failure == "read_error":
        assert feedback["error"] and feedback["rows_dropped"] > 0
    else:
        assert feedback["truncated"] and len(feedback["rows"]) == 2


def test_moving_entry_can_brake_before_drive_readiness(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    d.p[0], d.p[2] = .12, .2

    def brake():
        d.p[:3] = 0

    d.on_step = brake
    d.run()
    d.clean()
    assert d.report["passed"] and d.report["feedback_complete"]
    assert d.commands[0][:3] == (0., 0., 0.)
    assert not d.report["samples"][0]["raw_proprio_settled"]
