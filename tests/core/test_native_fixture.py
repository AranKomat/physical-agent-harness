import pytest

from experiments.fixtures.native import NativeFixtureBridge, UnknownRadioWorld
from physical_harness.core.contracts import SkillReceipt, VerificationResult, VerificationVerdict
from physical_harness.core.evidence import EvidenceStore
from physical_harness.reasoning.verification import VerificationRouter
from physical_harness.world.memory import DecisionCutoffLog, MemorySidecar, MemoryStore
from physical_harness.world.state import WorldState


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


def test_radio_fixture_records_memory_shadow_without_changing_decisions(tmp_path):
    blobs = EvidenceStore(tmp_path / "evidence")
    first = blobs.put(b"first legal image", ".jpg")
    second = blobs.put(b"second legal image", ".jpg")
    memory = MemoryStore(tmp_path / "episodic.sqlite", "episode", blobs.read)
    decisions = DecisionCutoffLog(tmp_path / "memory-decisions.sqlite", "episode")
    sidecar = MemorySidecar(
        episode_id="episode",
        store=memory,
        decisions=decisions,
        resolve_rgb_ref=lambda ref: ref,
    )

    def envelope(observation_id, sim_time, ref):
        return {
            "schema_version": 1,
            "episode_id": "episode",
            "observation_id": observation_id,
            "sim_time": sim_time,
            "rgb_refs": {"head": ref},
            "depth_refs": {"head": "depth"},
            "proprioception": {"joint_positions": [0.0]},
            "camera_intrinsics": {
                "head": {
                    "width": 16,
                    "height": 12,
                    "fx": 10.0,
                    "fy": 10.0,
                    "cx": 8.0,
                    "cy": 6.0,
                    "depth_scale_m": 0.001,
                }
            },
            "camera_frames": {"head": "head_optical"},
        }

    sidecar.ingest_observation(envelope("before", 0.0, first))
    with WorldState(tmp_path / "world.sqlite", "episode") as state:
        bridge = NativeFixtureBridge(
            state,
            memory_sidecar=sidecar,
            current_place_id="radio-room",
        )

        def execute(request):
            sidecar.ingest_observation(envelope("after", 0.5, second))
            return SkillReceipt(
                request.skill_id,
                "fixture",
                "completed",
                0,
                0.5,
                evidence_ids=("after",),
            )

        result = bridge.execute("chunk-0", 0, execute)

    assert result["event"]["type"] == "verifier_uncertain"
    assert result["task_status"] == "needs_verification"
    assert not result["finished"]
    assert len(result["memory_shadow"]) == 2
    assert all(not item["active"] for item in result["memory_shadow"])
    assert [decisions.status(item["decision"]["decision_id"]) for item in result["memory_shadow"]] == [
        "finalized",
        "finalized",
    ]
    cards = memory.cards(memory.cutoff(0.5))
    assert [card.event_type for card in cards] == ["decision_required", "verifier_uncertain"]
    assert all(card.entity_ids == ("radio",) for card in cards)
    assert all(card.place_ids == ("radio-room",) for card in cards)
    decisions.close()
    memory.close()


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
