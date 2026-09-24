"""Local contracts for matched control/transit and fresh post-handoff exposure."""

from copy import deepcopy

import numpy as np
import pytest

from experiments.behavior import exploratory_transit as transit
from experiments.behavior import hybrid_short
from experiments.behavior.contracts import Observation, Stamp

from .test_exploratory_transit import Driver


@pytest.mark.parametrize("control_only", [False, True])
def test_matched_intervention_has_same_stop_phases(monkeypatch, tmp_path, control_only):
    d = Driver(monkeypatch, tmp_path)
    final = d.run(control_only=control_only)
    d.clean()
    report = d.report
    assert report["passed"] and report["feedback_complete"]
    assert report["prehold_experimental_stop"] and report["experimental_stop_observed"]
    assert report["actions_completed"] == len(d.commands) == 92
    middle = "control_hold" if control_only else "move"
    assert [row["phase"] for row in report["commands"]] == (
        ["prehold"] * 6 + [middle] * 80 + ["final_hold"] * 6
    )
    assert d.moving == (0 if control_only else 80)
    assert report["commanded_integral_m"] == pytest.approx(0 if control_only else .08)
    assert report["measured_path_m"] == pytest.approx(0 if control_only else .08)
    assert all(command[3:] == d.commands[0][3:] for command in d.commands)
    if control_only:
        assert all(command[:3] == (0., 0., 0.) for command in d.commands)
    assert len(d.saved[-1]["feedback"]["rows"]) == 4 * 92
    assert final.stamp.sequence == 768 + 92
    assert final.observed_at > d.initial.observed_at
    assert d.capture_count == 95
    assert not report["strict_gate_passed"] and report["clearance"] == "unknown"


@pytest.mark.parametrize("failure", ["target", "capture", "icp", "drift", "speed", "switch"])
def test_control_hold_retains_guards_and_only_brakes(monkeypatch, tmp_path, failure):
    d = Driver(monkeypatch, tmp_path)

    def fail_during_control():
        if len(d.commands) != 7:
            return
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

    d.on_step = fail_during_control
    d.run(control_only=True)
    d.clean()
    assert not d.report["passed"]
    assert d.moving == 0 and d.report["commanded_integral_m"] == 0
    assert 1 <= d.report["brake_attempts"] <= 60
    assert all(command[:3] == (0., 0., 0.) for command in d.commands)
    assert all(row["phase"] == "abort_brake" for row in d.report["commands"][7:])
    policy = PolicyDriver(offset=d.sequence)
    policy.report["exploratory_transit"] = d.saved[-1]
    with pytest.raises((ValueError, RuntimeError)):
        policy.run()
    assert not policy.resets and not policy.inferences and not policy.commands


def test_control_requires_target_before_any_action(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    d.target_fail = True
    d.run(control_only=True)
    d.clean()
    assert not d.commands and not d.report["passed"]
    assert not d.report["experimental_stop_observed"]
    assert d.report["brake_attempts"] == 0


def test_control_missing_feedback_cannot_pass(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    monkeypatch.setattr(transit.FeedbackDiagnostic, "_capture", lambda _: None)
    d.run(control_only=True)
    d.clean()
    assert not d.report["passed"] and not d.report["feedback_complete"]
    assert d.moving == 0
    assert all(command[:3] == (0., 0., 0.) for command in d.commands)


def test_control_terminal_episode_never_steps_again(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    d.terminate = True
    d.run(control_only=True)
    d.clean()
    assert len(d.commands) == 1 and d.report["brake_attempts"] == 0
    assert d.report["episode_ended"] and not d.report["passed"]
    assert d.commands[0][:3] == (0., 0., 0.)


def test_control_path_limit_rejects_instead_of_shortening_exposure(monkeypatch, tmp_path):
    d = Driver(monkeypatch, tmp_path)
    original = d.icp

    def displaced_control(*args):
        if len(d.commands) == 7:
            transform = np.eye(4)
            transform[0, 3] = .08
            return True, transform, np.eye(6)
        return original(*args)

    monkeypatch.setattr(transit, "point_to_plane", displaced_control)
    d.run(control_only=True)
    d.clean()
    assert not d.report["passed"]
    assert "path bound" in d.report["error"]
    assert d.report["measured_path_m"] == pytest.approx(.08)
    phases = [row["phase"] for row in d.report["commands"]]
    assert phases.count("control_hold") == 1 and "final_hold" not in phases
    assert d.report["brake_attempts"] > 0
    assert d.moving == 0 and d.report["commanded_integral_m"] == 0
    assert all(command[:3] == (0., 0., 0.) for command in d.commands)


class PolicyDriver:
    """Native step owns the outer counter, just as it does in hybrid_short.main."""

    def __init__(self, offset=860, end_after=None):
        self.report = {
            "policy_actions": 768,
            "native_actions": offset,
            "policy_chunks": [{"policy_start": 0, "acquisition": True}],
            "exploratory_transit": {"report": {
                "passed": True, "feedback_complete": True,
                "experimental_stop_observed": True, "episode_ended": False,
            }},
        }
        self.offset = offset
        self.end_after = end_after
        self.resets, self.inferences, self.commands = [], [], []
        self.captures, self.saved, self.preprocessing_calls = [], [], []
        self.observation = self.capture()

    def reset(self, stamp):
        self.resets.append(deepcopy(stamp))
        assert not self.commands
        assert stamp == self.observation.stamp.model_dump()
        post = self.report["post_handoff"]
        assert post["policy_actions"] == 0
        assert post["native_actions"] == self.offset
        assert post["policy_chunks"] == []
        return {"stamp": stamp}

    def infer(self, packet):
        assert len(self.resets) == 1
        assert packet["stamp"] == self.captures[-1].stamp.model_dump()
        self.inferences.append(deepcopy(packet["stamp"]))
        return {"stamp": packet["stamp"], "actions": np.zeros((32, 23))}

    def step(self, action):
        assert np.asarray(action).shape == (23,)
        self.commands.append(np.asarray(action).copy())
        self.report["native_actions"] += 1
        return len(self.commands) == self.end_after

    def capture(self):
        sequence = self.report["native_actions"]
        observation = Observation(
            stamp=Stamp(session="matched", epoch=3, sequence=sequence),
            observed_at=float(sequence), proprio=(0.,) * 61, rgb={},
        )
        self.captures.append(observation)
        return observation

    def save(self):
        self.saved.append(deepcopy(self.report))

    def preprocessing(self, actions):
        self.preprocessing_calls.append(actions.copy())
        return "checked-post-handoff"

    def run(self):
        return hybrid_short.execute_post_handoff(
            self, self.observation, None, self.step, self.capture,
            self.report, self.save, self.preprocessing,
        )


@pytest.mark.parametrize("offset", [860, 885, 4096])
def test_post_handoff_resets_and_runs_384_independent_of_native_offset(offset):
    d = PolicyDriver(offset)
    acquisition = deepcopy(d.report["policy_chunks"])
    final = d.run()
    post = d.report["post_handoff"]
    assert post["reset_sequence"] == offset
    assert d.resets == [d.observation.stamp.model_dump()]
    assert [stamp["sequence"] for stamp in d.inferences] == list(range(offset, offset + 384, 32))
    assert len(d.commands) == post["policy_actions"] == 384
    assert post["native_actions"] == d.report["native_actions"] == offset + 384
    assert d.report["policy_actions"] == 768
    assert d.report["policy_chunks"] == acquisition
    assert post["policy_chunks"] is not d.report["policy_chunks"]
    assert [chunk["policy_start"] for chunk in post["policy_chunks"]] == list(range(0, 384, 32))
    assert [chunk["native_start"] for chunk in post["policy_chunks"]] == list(
        range(offset, offset + 384, 32)
    )
    assert d.report["total_policy_actions"] == 1152
    assert post["completed"] is True
    assert post["preprocessing_proof"] == "checked-post-handoff"
    assert len(d.preprocessing_calls) == 1
    assert final.stamp.sequence == offset + 384
    assert final.stamp.same_episode(d.observation.stamp)
    assert len(d.captures) == 13
    assert d.saved[-1]["total_policy_actions"] == 1152
    assert d.saved[-1]["post_handoff"]["native_actions"] == offset + 384


@pytest.mark.parametrize("field", ["passed", "feedback_complete", "experimental_stop_observed"])
@pytest.mark.parametrize("missing", [False, True])
def test_failed_or_incomplete_probe_never_resets_or_runs_policy(field, missing):
    d = PolicyDriver()
    probe = d.report["exploratory_transit"]["report"]
    if missing:
        del probe[field]
    else:
        probe[field] = False
    with pytest.raises((ValueError, RuntimeError)):
        d.run()
    assert not d.resets and not d.inferences and not d.commands
    assert len(d.captures) == 1
    assert d.report["native_actions"] == d.offset


@pytest.mark.parametrize("actions", [None, -1, 0, 767, 769, "768"])
def test_malformed_acquisition_never_resets_or_runs_policy(actions):
    d = PolicyDriver()
    if actions is None:
        del d.report["policy_actions"]
    else:
        d.report["policy_actions"] = actions
    with pytest.raises((ValueError, RuntimeError)):
        d.run()
    assert not d.resets and not d.inferences and not d.commands
    assert d.report["native_actions"] == d.offset


@pytest.mark.parametrize("failure", ["native_end", "stale_observation", "missing_probe", "missing_report"])
def test_invalid_handoff_boundary_never_uses_policy(failure):
    d = PolicyDriver()
    if failure == "native_end":
        d.report["native_end"] = True
    elif failure == "stale_observation":
        d.report["native_actions"] += 1
    elif failure == "missing_probe":
        del d.report["exploratory_transit"]
    else:
        del d.report["exploratory_transit"]["report"]
    native_before = d.report["native_actions"]
    with pytest.raises((ValueError, RuntimeError)):
        d.run()
    assert not d.resets and not d.inferences and not d.commands
    assert d.report["native_actions"] == native_before


def test_post_handoff_cannot_be_repeated():
    d = PolicyDriver()
    d.observation = d.run()
    completed = deepcopy(d.report)
    with pytest.raises((ValueError, RuntimeError)):
        d.run()
    assert len(d.resets) == 1 and len(d.commands) == 384
    assert len(d.inferences) == 12
    assert d.report == completed


@pytest.mark.parametrize("end_after", [1, 32, 383])
def test_early_post_handoff_end_rejected_without_extra_policy(end_after):
    d = PolicyDriver(end_after=end_after)
    with pytest.raises((ValueError, RuntimeError)):
        d.run()
    post = d.report["post_handoff"]
    assert len(d.resets) == 1
    assert len(d.commands) == post["policy_actions"] == end_after
    assert len(d.inferences) == (end_after + 31) // 32
    assert post["native_end"] is True
    assert not post.get("completed", False)
    assert post["native_actions"] == d.report["native_actions"] == d.offset + end_after
    assert d.report["policy_actions"] == 768
    assert d.report.get("total_policy_actions") != 1152


def _cli(monkeypatch, tmp_path, condition, flags):
    monkeypatch.setattr("sys.argv", [
        "hybrid-short", "--source", str(tmp_path), "--output", str(tmp_path / "out"),
        "--policy-load-receipt", str(tmp_path / "receipt"), "--condition", condition,
        "--allow-simulator", "--allow-unknown-clearance-exploration", "--licenses-accepted",
        "--matched-target-handoff", *flags,
    ])

    def source_preflight(*args):
        raise LookupError("reached source preflight")

    monkeypatch.setattr(hybrid_short, "check_source", source_preflight)


MATCHED_FLAGS = ["--extended-grounding-acquisition", "--grounding-port", "8021",
                 "--robot-assets", "unused"]


@pytest.mark.parametrize("condition", ["A", "B"])
def test_matched_cli_accepts_both_conditions(monkeypatch, tmp_path, condition):
    _cli(monkeypatch, tmp_path, condition, MATCHED_FLAGS)
    with pytest.raises(LookupError, match="reached source preflight"):
        hybrid_short.main()
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("condition", ["A", "B"])
def test_matched_sam_cli_accepts_both_conditions(monkeypatch, tmp_path, condition):
    _cli(monkeypatch, tmp_path, condition, [
        "--extended-grounding-acquisition", "--sam-exploratory-transit",
        "--robot-assets", "unused",
    ])
    with pytest.raises(LookupError, match="reached source preflight"):
        hybrid_short.main(sam_probe=object())
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("condition", ["A", "B"])
@pytest.mark.parametrize("incompatible", [
    "--exploratory-transit", "--assisted-target-probe", "--feedback-hold-diagnostic",
])
def test_matched_cli_rejects_combined_modes(monkeypatch, tmp_path, condition, incompatible):
    _cli(monkeypatch, tmp_path, condition, [*MATCHED_FLAGS, incompatible])
    with pytest.raises(SystemExit) as exc:
        hybrid_short.main()
    assert exc.value.code == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("required", [
    "--extended-grounding-acquisition", "--grounding-port", "--robot-assets",
])
@pytest.mark.parametrize("condition", ["A", "B"])
def test_matched_cli_requires_acquisition_grounding_and_assets(
    monkeypatch, tmp_path, required, condition,
):
    flags = MATCHED_FLAGS.copy()
    index = flags.index(required)
    del flags[index:index + (1 if required == "--extended-grounding-acquisition" else 2)]
    _cli(monkeypatch, tmp_path, condition, flags)
    with pytest.raises(SystemExit) as exc:
        hybrid_short.main()
    assert exc.value.code == 2
    assert not (tmp_path / "out").exists()
