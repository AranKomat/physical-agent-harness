import pytest

from physical_harness.contracts import (
    SkillReceipt,
    VerificationResult,
    VerificationVerdict,
)
from physical_harness.native_fixture import NativeFixtureBridge, UnknownRadioWorld
from physical_harness.state import WorldState
from physical_harness.verification import VerificationRouter


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


def test_injected_observer_verifier_and_completion_hook_close_ledger(tmp_path):
    class Verifier:
        name = "qualified-test-verifier"

        def verify(self, request):
            assert request.before_evidence_ids == ("before",)
            assert request.after_evidence_ids == ("after",)
            return VerificationResult(
                request.request_id,
                self.name,
                VerificationVerdict.VERIFIED,
                0.99,
                ("after",),
                "Visible test support.",
            )

    with WorldState(tmp_path / "world.sqlite", "episode") as state:
        state.add_evidence("before", 0, "perception", "before.png", {})
        state.add_evidence("after", 0.5, "perception", "after.png", {})
        bridge = None

        def on_verified(request, receipt, verification):
            assert request.skill_id == receipt.skill_id
            assert verification.evidence_ids == ("after",)
            state.update("radio", "power", "on", "after")
            bridge.ledger.set_status(
                "radio", "observed_complete", "after", now=receipt.sim_time_end
            )

        bridge = NativeFixtureBridge(
            state,
            verifier=VerificationRouter(UnknownRadioWorld(), frontier=Verifier()),
            after_observer=lambda request, receipt: ("after",),
            on_verified=on_verified,
        )

        result = bridge.execute(
            "chunk-0",
            0,
            lambda request: SkillReceipt(
                request.skill_id,
                "fixture",
                "completed",
                0,
                0.5,
                evidence_ids=("motor-evidence",),
            ),
            before_evidence_ids=("before",),
        )

        assert result["event"]["type"] == "skill_verified"
        assert result["task_status"] == "observed_complete"
        assert result["finished"]


def test_injected_observer_requires_fresh_evidence_ids(tmp_path):
    with WorldState(tmp_path / "world.sqlite", "episode") as state:
        bridge = NativeFixtureBridge(state, after_observer=lambda request, receipt: ())
        with pytest.raises(ValueError, match="fresh evidence"):
            bridge.execute(
                "chunk",
                0,
                lambda request: SkillReceipt(
                    request.skill_id,
                    "fixture",
                    "completed",
                    0,
                    0.5,
                ),
            )


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
