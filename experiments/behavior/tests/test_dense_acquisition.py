"""Extra shadow captures must not affect the policy's action/observation path."""

import numpy as np
import pytest

from experiments.behavior import hybrid_short
from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.hybrid_short import execute_policy


def run(dense, end_after=None, budget=768):
    report = {"native_actions": 0, "policy_actions": 0, "policy_chunks": []}
    commands, requests, captures, shadows = [], [], [], []

    def capture():
        sequence = report["native_actions"]
        captures.append(sequence)
        return Observation(stamp=Stamp(session="dense", epoch=0, sequence=sequence),
                           observed_at=float(sequence), proprio=(0.,) * 61, rgb={})

    class Transport:
        def reset(self, stamp):
            return {"stamp": stamp}

        def infer(self, packet):
            requests.append(packet)
            # Different actions per chunk catch accidental reuse or skipped actions.
            return {"stamp": packet["stamp"],
                    "actions": np.full((32, 23), len(requests) / 100.)}

    def step(action):
        commands.append(action.copy())
        report["native_actions"] += 1
        return report["native_actions"] == end_after

    final = execute_policy(Transport(), capture(), None, step, capture, report,
                           lambda: None, lambda actions: True, action_budget=budget,
                           dense_capture=(lambda: shadows.append(report["native_actions"])) if dense else None)
    return report, commands, requests, captures, shadows, final


@pytest.mark.parametrize("end_after", [None, 388, 389, 512])
def test_dense_preserves_policy_path_and_native_end(end_after):
    plain, dense = run(False, end_after), run(True, end_after)
    assert np.array_equal(plain[1], dense[1])
    assert plain[2:4] == dense[2:4]
    assert plain[5] == dense[5]
    assert plain[0].get("native_end") == dense[0].get("native_end")
    stop = end_after or 769
    expected = [n for n in range(384, 513, 4) if n % 32 and n < stop]
    assert dense[4] == expected
    assert plain[0]["policy_actions"] == dense[0]["policy_actions"] == min(stop, 768)


def test_dense_rejects_short_budget_before_policy():
    with pytest.raises(ValueError, match="extended acquisition"):
        run(True, budget=384)


@pytest.mark.parametrize("extra", [[], ["--condition", "B"], ["--exploratory-transit"],
    ["--matched-target-handoff"], ["--feedback-hold-diagnostic"], ["--assisted-target-probe"]])
def test_dense_cli_is_isolated(monkeypatch, tmp_path, extra):
    monkeypatch.setattr("sys.argv", [
        "hybrid-short", "--source", str(tmp_path), "--output", str(tmp_path / "out"),
        "--policy-load-receipt", str(tmp_path / "receipt"), "--condition", "A",
        "--allow-simulator", "--allow-unknown-clearance-exploration", "--licenses-accepted",
        "--extended-grounding-acquisition", "--grounding-port", "8021",
        "--robot-assets", str(tmp_path), "--dense-observation-diagnostic", *extra,
    ])

    def preflight(*args):
        raise LookupError("source preflight")

    monkeypatch.setattr(hybrid_short, "check_source", preflight)
    with pytest.raises(SystemExit if extra else LookupError):
        hybrid_short.main()
    assert not (tmp_path / "out").exists()
