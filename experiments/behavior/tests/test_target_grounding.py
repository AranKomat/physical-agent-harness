import copy
import json
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.behavior import target_grounding
from experiments.behavior.contracts import Observation, Stamp
from experiments.behavior.grounding_manifest import (
    online_identity,
    validate_online_identity,
    verify_files,
)
from experiments.behavior.observations import EvidenceStore
from experiments.behavior.target_grounding import (
    GroundingBackend,
    RobotSelfCheck,
    ground_capture,
    read_grounding_packet,
    save_result,
    validate_packet,
)


def packet(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    stamp = Stamp(session="grounding", epoch=0, sequence=32)
    rgb = np.zeros((720, 720, 3), dtype=np.uint8)
    depth = np.ones((720, 720), dtype=np.float32)
    obs = Observation(stamp=stamp, observed_at=1., proprio=(0.,)*61,
                      rgb={"head": store.put(rgb, "rgb", stamp, 1.)},
                      depth={"head": store.put(depth, "depth", stamp, 1.)})
    k = {"stamp": stamp.model_dump(), "observed_at": 1., "rgb_evidence_id": obs.rgb["head"].id,
         "depth_evidence_id": obs.depth["head"].id, "image_shape": [720, 720],
         "intrinsic_matrix": [[500., 0, 360], [0, 500., 360], [0, 0, 1]]}
    return {"observation": obs.model_dump(), "calibration": {"head": k}, "rgb": rgb, "depth": depth}


def test_packet_requires_same_boundary_calibration(tmp_path):
    p = packet(tmp_path)
    assert validate_packet(p)[0].stamp.sequence == 32
    for field in ("rgb_evidence_id", "depth_evidence_id", "observed_at", "stamp"):
        q = copy.deepcopy(p)
        q["calibration"]["head"][field] = None
        with pytest.raises(ValueError, match="detached"):
            validate_packet(q)


@pytest.mark.parametrize("field", ["rgb", "depth"])
def test_packet_rejects_misaligned_arrays(tmp_path, field):
    p = packet(tmp_path)
    p[field] = p[field][:-1]
    with pytest.raises(ValueError, match="aligned"):
        validate_packet(p)


def test_mask_artifact_preserves_source_binding_and_is_not_sensor_depth(tmp_path):
    p = packet(tmp_path)
    result = {"stamp": p["observation"]["stamp"], "rgb_evidence_id": p["observation"]["rgb"]["head"]["id"],
              "candidates": [{"mask": np.ones((720, 720), dtype=bool)}]}
    saved = save_result(result, tmp_path / "derived")
    mask = saved["candidates"][0]["derived_mask"]
    assert mask["stamp"] == result["stamp"]
    assert mask["rgb_evidence_id"] == result["rgb_evidence_id"]
    assert np.load(tmp_path / "derived" / mask["uri"], allow_pickle=False).dtype == bool
    assert "mask" not in saved["candidates"][0]


@pytest.mark.parametrize("corrupt", [False, True])
def test_online_capture_rejects_stale_service_result(tmp_path, corrupt):
    p = packet(tmp_path)
    obs = Observation.model_validate(p["observation"])

    class Transport:
        def infer(self, sent):
            assert sent["observation"] == p["observation"]
            return {"stamp": {} if corrupt else obs.stamp.model_dump(),
                    "rgb_evidence_id": obs.rgb["head"].id, "depth_evidence_id": obs.depth["head"].id,
                    "motion_authorized": False, "candidates": [], "identity": online_identity()}

    row = {key: p[key] for key in ("observation", "calibration")}
    if corrupt:
        with pytest.raises(ValueError, match="stale"):
            ground_capture(row, EvidenceStore(tmp_path / "evidence"), Transport(), tmp_path / "masks")
    else:
        result = ground_capture(row, EvidenceStore(tmp_path / "evidence"), Transport(), tmp_path / "masks")
        assert result["delivery"] == "synchronous_online_shadow_before_next_policy_chunk"
        assert not result["motion_authorized"]


@pytest.mark.parametrize("distance, rejected", [(.1, True), (.5, False)])
def test_near_hand_filter_only_marks_ambiguity_not_semantic_truth(tmp_path, distance, rejected):
    obs = Observation.model_validate(packet(tmp_path)["observation"])
    checker = RobotSelfCheck.__new__(RobotSelfCheck)
    candidate = {"surface_median_camera_m": [distance, 0., 0.]}
    checker.annotate(candidate, obs, np.eye(4))
    assert ("rejected" in candidate) == rejected
    assert candidate["eef_distances_m"] == [distance, distance]
    assert "motion_authorized" not in candidate


@pytest.mark.parametrize("key", list(online_identity()))
def test_frozen_online_configuration_rejects_changed_service(key):
    identity = online_identity()
    validate_online_identity(identity)
    identity[key] = None
    with pytest.raises(ValueError, match="frozen online"):
        validate_online_identity(identity)


def test_snapshot_checks_actual_contents_and_extra_loader_config(tmp_path):
    import hashlib

    path = tmp_path / "config.json"
    path.write_bytes(b"{}")
    expected = {"config.json": hashlib.sha256(b"{}").hexdigest()}
    assert verify_files(tmp_path, expected) == expected
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="content mismatch"):
        verify_files(tmp_path, expected)
    path.write_bytes(b"{}")
    (tmp_path / "processor_config.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="Unexpected"):
        verify_files(tmp_path, expected)


class FakeTensor:
    def __init__(self, values):
        self.values = np.asarray(values)

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.values

    def __getitem__(self, index):
        value = self.values[index]
        return FakeTensor(value) if isinstance(value, np.ndarray) else value


@pytest.mark.parametrize("distractor_count,target_count", [(4, 1), (6, 7), (0, 0), (0, 2)])
def test_infer_caps_targets_separately_and_reports_omissions(
        tmp_path, monkeypatch, distractor_count, target_count):
    labels = ["a television"] * distractor_count + ["a radio"] * target_count
    count = len(labels)
    detections = {"scores": FakeTensor(np.linspace(.99, .41, count)),
                  "boxes": FakeTensor([[i, 10, i + 20, 30] for i in range(count)]),
                  "text_labels": labels}

    class Inputs(dict):
        input_ids = None

        def to(self, device):
            return self

    class Processor:
        def __call__(self, **kwargs):
            return Inputs()

        def post_process_grounded_object_detection(self, *args, **kwargs):
            return [detections]

    backend = GroundingBackend.__new__(GroundingBackend)
    backend.processor = Processor()
    backend.model = lambda **kwargs: None
    backend.torch = SimpleNamespace(inference_mode=nullcontext)
    backend.prompt, backend.identity, backend.self_check = "a radio.", {}, None
    segmented_boxes = []

    def segment(rgb, depth, box, k):
        segmented_boxes.append(box)
        return {"mask_pixels": 20}

    monkeypatch.setattr(target_grounding, "segmented_depth", segment)
    result = backend.infer(packet(tmp_path))
    assert len(result["candidates"]) == min(4, target_count)
    assert len(result["distractors"]) == min(4, distractor_count)
    assert result["omitted_target_count"] == max(0, target_count - 4)
    assert result["omitted_distractor_count"] == max(0, distractor_count - 4)
    assert result["target_candidate_limit"] == result["distractor_limit"] == 4
    assert [box[0] for box in segmented_boxes] == list(
        range(distractor_count, distractor_count + min(4, target_count)))
    assert not result["motion_authorized"]


@pytest.mark.parametrize("modality", ["rgb", "depth"])
@pytest.mark.parametrize("corruption", ["substituted_uri", "content", "identity", "path", "suffix"])
def test_ground_capture_rejects_corrupt_evidence_before_rpc(
        tmp_path, modality, corruption):
    p = packet(tmp_path)
    store = EvidenceStore(tmp_path / "evidence")
    ref = p["observation"][modality]["head"]
    if corruption == "substituted_uri":
        replacement = np.full_like(p[modality], 42)
        other = store.put(replacement, modality, Stamp.model_validate(ref["stamp"]), 1.)
        ref["uri"] = other.uri
    elif corruption == "content":
        (store.root / ref["uri"]).write_bytes(b"not the recorded bytes")
    elif corruption == "identity":
        ref["id"] = "0" * 64
        p["calibration"]["head"][modality + "_evidence_id"] = ref["id"]
    elif corruption == "path":
        ref["uri"] = "../" + ref["uri"]
    else:
        ref["uri"] = ref["uri"].rsplit(".", 1)[0] + (".npy" if modality == "rgb" else ".png")

    class Transport:
        def infer(self, sent):
            pytest.fail("Corrupt evidence reached RPC")

    row = {key: p[key] for key in ("observation", "calibration")}
    with pytest.raises(ValueError, match="Grounding evidence"):
        ground_capture(row, store, Transport(), tmp_path / "masks")
    assert not (tmp_path / "masks").exists()


def test_ground_capture_validates_calibration_before_rpc(tmp_path):
    p = packet(tmp_path)
    p["calibration"]["head"]["observed_at"] = 2.
    transport = SimpleNamespace(infer=lambda _: pytest.fail("Invalid calibration reached RPC"))
    with pytest.raises(ValueError, match="detached"):
        ground_capture(p, EvidenceStore(tmp_path / "evidence"), transport, tmp_path / "masks")


def test_read_grounding_packet_decodes_verified_bytes_without_store_reread(tmp_path, monkeypatch):
    p = packet(tmp_path)
    store = EvidenceStore(tmp_path / "evidence")
    monkeypatch.setattr(store, "read", lambda _: pytest.fail("Do not reread unverified bytes"))
    before = {path.name: path.read_bytes() for path in store.root.iterdir()}
    result = read_grounding_packet(p, store)
    np.testing.assert_array_equal(result["rgb"], p["rgb"])
    np.testing.assert_array_equal(result["depth"], p["depth"])
    assert before == {path.name: path.read_bytes() for path in store.root.iterdir()}


@pytest.mark.parametrize("corrupt", [False, True])
def test_offline_replay_uses_verified_evidence_before_inference(tmp_path, monkeypatch, corrupt):
    p = packet(tmp_path)
    store = EvidenceStore(tmp_path / "evidence")
    if corrupt:
        ref = p["observation"]["rgb"]["head"]
        ref["uri"] = store.put(np.full_like(p["rgb"], 42), "rgb",
                               Stamp.model_validate(ref["stamp"]), 1.).uri
    row = {key: p[key] for key in ("observation", "calibration")}
    (tmp_path / "hybrid_short.json").write_text(json.dumps({"captures": [row]}))
    calls = []

    class Backend:
        identity = {}

        def __init__(self, *args):
            pass

        def infer(self, sent):
            if corrupt:
                pytest.fail("Substituted pixels reached offline inference")
            calls.append(sent)
            return {"candidates": []}

    monkeypatch.setattr(target_grounding, "GroundingBackend", Backend)
    monkeypatch.setattr("sys.argv", ["grounding", "--checkpoint", "unused",
                                    "--runs", str(tmp_path), "--output", str(tmp_path / "out")])
    if corrupt:
        with pytest.raises(ValueError, match="identity hash"):
            target_grounding.main()
        assert calls == []
    else:
        target_grounding.main()
        assert len(calls) == 1
        np.testing.assert_array_equal(calls[0]["rgb"], p["rgb"])
