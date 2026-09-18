import pytest

from physical_harness.contracts import SkillReceipt
from physical_harness.native_fixture import NativeFixtureBridge
from physical_harness.state import WorldState


def test_live_callback_drives_events_without_inventing_success(tmp_path):
    with WorldState(tmp_path / "world.sqlite", "episode") as state:
        bridge = NativeFixtureBridge(state)
        calls = []

        def execute(request):
            calls.append(request)
            state.add_evidence("obs", 0.5, "telemetry", "obs.json", {"proprio": [1]})
            state.update("robot", "proprio", "[1]", "obs")
            return SkillReceipt(
                request.skill_id,
                "fixture",
                "completed",
                0,
                0.5,
                action_steps_executed=15,
                evidence_ids=("obs",),
            )

        result = bridge.execute("chunk-0", 0, execute)
        assert len(calls) == 1
        assert result["event"]["type"] == "verifier_uncertain"
        assert result["task_status"] == "needs_verification"
        assert not result["finished"]
        assert result["executive_calls"] == 2
        assert state.belief("radio", "power") is None
        assert state.belief("robot", "proprio")["evidence_id"] == "obs"
        with pytest.raises(ValueError):
            bridge.execute("chunk-0", 0, execute)
        with pytest.raises(ValueError):
            bridge.execute("chunk-1", 0, execute)
        assert len(calls) == 1


def test_ambiguous_callback_failure_is_not_retried(tmp_path):
    with WorldState(tmp_path / "world.sqlite", "episode") as state:
        bridge = NativeFixtureBridge(state)

        def failed(request):
            raise RuntimeError("partial native execution")

        with pytest.raises(RuntimeError):
            bridge.execute("chunk", 0, failed)
        with pytest.raises(ValueError):
            bridge.execute("chunk", 0, failed)


@pytest.mark.parametrize("end", [float("nan"), float("inf"), 0, -1])
def test_invalid_receipt_clock_cannot_advance_bridge(tmp_path, end):
    with WorldState(tmp_path / "world.sqlite", "episode") as state:
        bridge = NativeFixtureBridge(state)
        with pytest.raises(ValueError, match="clock"):
            bridge.execute(
                "chunk",
                0,
                lambda request: SkillReceipt(
                    request.skill_id,
                    "fixture",
                    "completed",
                    0,
                    end,
                ),
            )
        assert bridge.last_end == 0
        assert bridge.records == []
