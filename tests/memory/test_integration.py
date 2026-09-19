from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from physical_harness.evidence import EvidenceStore
from physical_harness.memory.integration import DecisionCutoffLog, MemorySidecar
from physical_harness.memory.schemas import Draft, PacketBudget
from physical_harness.memory.spatial_views import SpatialViewIndex
from physical_harness.memory.store import MemoryStore


@dataclass(frozen=True)
class Event:
    type: str
    episode_id: str
    sim_time: float
    payload: dict
    event_id: str


def image(store, value: bytes):
    return store.put(value, ".jpg")


def envelope(ep, obs, t, ref):
    return {
        "schema_version": 1,
        "episode_id": ep,
        "observation_id": obs,
        "sim_time": t,
        "rgb_refs": {"head": ref},
        "depth_refs": {"head": "unused-depth"},
        "proprioception": {"joint_positions": [0.0]},
        "camera_intrinsics": {
            "head": {
                "width": 10, "height": 10, "fx": 5.0, "fy": 5.0,
                "cx": 5.0, "cy": 5.0, "depth_scale_m": 0.001,
            }
        },
        "camera_frames": {"head": "head_optical"},
    }


def posed_envelope(ep, obs, t, ref):
    value = envelope(ep, obs, t, ref)
    value["estimated_pose"] = {
        "method": "rgbd_odometry",
        "frame": "local_map",
        "camera": "head",
        "transform": [
            [1, 0, 0, 1],
            [0, 1, 0, 2],
            [0, 0, 1, 1],
            [0, 0, 0, 1],
        ],
        "evidence_ids": [obs],
        "confidence": 0.9,
    }
    return value


def setup(tmp_path):
    blobs = EvidenceStore(tmp_path / "evidence")
    memory = MemoryStore(tmp_path / "episodic.sqlite", "ep", blobs.read)
    decisions = DecisionCutoffLog(tmp_path / "decisions.sqlite", "ep")
    sidecar = MemorySidecar(
        episode_id="ep",
        store=memory,
        decisions=decisions,
        resolve_rgb_ref=lambda ref: ref,
    )
    return blobs, memory, decisions, sidecar


def test_observation_event_shadow_context(tmp_path):
    blobs, memory, decisions, sidecar = setup(tmp_path)
    ref = image(blobs, b"not-a-real-jpeg-but-hash-valid")
    assets = sidecar.ingest_observation(envelope("ep", "o1", 1.0, ref))
    assert len(assets) == 1
    sidecar.bind_skill("s1", entity_ids=("candle_1",), place_ids=("kitchen",))
    card = sidecar.record_event(
        Event("skill_verified", "ep", 1.0, {"skill_id": "s1"}, "e1")
    )
    assert card.entity_ids == ("candle_1",)
    assert card.place_ids == ("kitchen",)
    base = {"episode": "ep", "goal": "put candle away", "images": []}
    result, decision, packet = sidecar.prepare_decision(
        decision_id="d1",
        event_id="e1",
        observed_through=1.0,
        base_context=base,
        entity_id="candle_1",
        active=False,
    )
    assert result == base
    assert "episodic_memory" not in result
    assert packet["cards"][0]["card_id"] == card.card_id
    assert decisions.get("d1") == decision
    memory.close()
    decisions.close()


def test_active_context_attaches_same_packet(tmp_path):
    blobs, memory, decisions, sidecar = setup(tmp_path)
    ref = image(blobs, b"frame")
    sidecar.ingest_observation(envelope("ep", "o1", 1.0, ref))
    sidecar.bind_skill("s1", entity_ids=("x",))
    sidecar.record_event(Event("skill_failed", "ep", 1.0, {"skill_id": "s1"}, "e1"))
    base = {"episode": "ep", "goal": "find x", "images": []}
    result, _, packet = sidecar.prepare_decision(
        decision_id="d1", event_id="e1", observed_through=1.0,
        base_context=base, entity_id="x", active=True,
        budget=PacketBudget(max_cards=2, max_images=1, max_pixels=1000, max_bytes=5000),
        max_total_bytes=8000,
    )
    assert json.loads(json.dumps(result["episodic_memory"])) == json.loads(json.dumps(packet))
    memory.close()
    decisions.close()


def test_opt_in_spatial_keyframe_is_shadow_only_and_serializable(tmp_path):
    blobs = EvidenceStore(tmp_path / "evidence")
    memory = MemoryStore(tmp_path / "episodic.sqlite", "ep", blobs.read)
    decisions = DecisionCutoffLog(tmp_path / "decisions.sqlite", "ep")
    spatial = SpatialViewIndex("ep")
    sidecar = MemorySidecar(
        episode_id="ep",
        store=memory,
        decisions=decisions,
        resolve_rgb_ref=lambda ref: ref,
        spatial_index=spatial,
    )
    ref = image(blobs, b"posed-frame")
    sidecar.ingest_observation(
        posed_envelope("ep", "o1", 1.0, ref),
        keyframe_reason="decision_required",
        keyframe_entity_ids=("cup",),
        keyframe_place_ids=("kitchen",),
    )
    snapshot_path = tmp_path / "spatial-memory.json"
    sidecar.write_spatial_snapshot(snapshot_path)
    restored = SpatialViewIndex.from_snapshot(json.loads(snapshot_path.read_text()))
    assert restored.snapshot() == spatial.snapshot()
    assert tuple(spatial.keyframes) == ("posed:o1:head",)

    base = {"episode": "ep", "goal": "find cup", "images": []}
    unchanged, _, _ = sidecar.prepare_decision(
        decision_id="d-spatial",
        event_id="e-spatial",
        observed_through=1.0,
        base_context=base,
        active=False,
    )
    assert unchanged == base
    assert "spatial_memory" not in unchanged
    memory.close()
    decisions.close()


def test_opt_in_spatial_memory_does_not_invent_pose(tmp_path):
    blobs = EvidenceStore(tmp_path / "evidence")
    memory = MemoryStore(tmp_path / "episodic.sqlite", "ep", blobs.read)
    decisions = DecisionCutoffLog(tmp_path / "decisions.sqlite", "ep")
    spatial = SpatialViewIndex("ep")
    sidecar = MemorySidecar(
        episode_id="ep",
        store=memory,
        decisions=decisions,
        resolve_rgb_ref=lambda ref: ref,
        spatial_index=spatial,
    )
    ref = image(blobs, b"unposed-frame")
    assets = sidecar.ingest_observation(
        envelope("ep", "o1", 1.0, ref), keyframe_reason="decision_required"
    )
    assert len(assets) == 1
    assert spatial.keyframes == {}
    memory.close()
    decisions.close()


def test_late_annotation_cannot_leak_into_saved_decision(tmp_path):
    blobs, memory, decisions, sidecar = setup(tmp_path)
    ref = image(blobs, b"frame")
    sidecar.ingest_observation(envelope("ep", "o1", 1.0, ref))
    card = sidecar.record_event(Event("decision_required", "ep", 1.0, {}, "e1"))
    base = {"episode": "ep", "goal": "g", "images": []}
    _, decision, packet_before = sidecar.prepare_decision(
        decision_id="d1", event_id="e1", observed_through=1.0,
        base_context=base, active=False,
    )
    memory.add_annotation(
        card.card_id,
        Draft("later caption", (card.asset_ids[0],)),
        model="fixture",
        prompt_id="p",
        basis=memory.cutoff(1.0),
        wall_seconds=0.1,
    )
    # Replay exactly the saved cutoff: later annotation must remain absent.
    hits = sidecar.retriever.search(decision.cutoff)
    replay = sidecar.retriever.packet(hits, decision.cutoff)
    assert replay == packet_before
    assert replay["cards"][0]["narration"] is None
    memory.close()
    decisions.close()


@pytest.mark.parametrize(
    "event_type",
    ["verifier_uncertain", "precondition_violated", "plan_exhausted", "path_blocked"],
)
def test_full_runtime_event_vocabulary_is_recordable(tmp_path, event_type):
    blobs, memory, decisions, sidecar = setup(tmp_path)
    ref = image(blobs, event_type.encode())
    sidecar.ingest_observation(envelope("ep", "o1", 1.0, ref))
    card = sidecar.record_event(Event(event_type, "ep", 1.0, {}, "e1"))
    assert card.event_type == event_type
    memory.close()
    decisions.close()


def test_requires_content_addressed_resolved_ref(tmp_path):
    blobs = EvidenceStore(tmp_path / "evidence")
    memory = MemoryStore(tmp_path / "episodic.sqlite", "ep", blobs.read)
    decisions = DecisionCutoffLog(tmp_path / "decisions.sqlite", "ep")
    sidecar = MemorySidecar(
        episode_id="ep", store=memory, decisions=decisions,
        resolve_rgb_ref=lambda ref: "opaque-reference",
    )
    with pytest.raises(ValueError, match="hash-named"):
        sidecar.ingest_observation(envelope("ep", "o1", 1.0, "native"))
    memory.close()
    decisions.close()


def test_decision_cutoff_is_reserved_before_packet_failure(tmp_path):
    blobs, memory, decisions, sidecar = setup(tmp_path)
    ref = image(blobs, b"frame")
    sidecar.ingest_observation(envelope("ep", "o1", 1.0, ref))
    sidecar.record_event(Event("decision_required", "ep", 1.0, {}, "e1"))
    with pytest.raises(ValueError):
        sidecar.prepare_decision(
            decision_id="crash-safe",
            event_id="e1",
            observed_through=1.0,
            base_context={"episode": "ep"},
            active=False,
            budget=PacketBudget(max_cards=1, max_images=1, max_pixels=1000, max_bytes=1),
        )
    saved = decisions.get("crash-safe")
    assert saved.cutoff.observed_through == 1.0
    assert decisions.status("crash-safe") == "reserved"
    memory.close()
    decisions.close()
