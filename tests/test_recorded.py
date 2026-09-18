import json

import pytest

from physical_harness.adapters.recorded import (
    BEHAVIOR_COMMIT,
    CAMERAS,
    audit_archive,
    decode_proprio,
    read_archive,
)
from physical_harness.evidence import EvidenceStore


def archive(tmp_path):
    store = EvidenceStore(tmp_path / "legal-evidence")
    stamp = {"session": "recorded", "epoch": 0, "sequence": 0}
    raw = {"stamp": stamp, "observed_at": 100, "proprio": list(range(61))}
    for modality, suffix in (("rgb", ".png"), ("depth", ".npy")):
        raw[modality] = {
            camera: {
                "stamp": stamp,
                "observed_at": 100,
                "source": modality,
                "uri": store.put(b"hash-test-fixture", suffix),
            }
            for camera in CAMERAS
        }
    metadata = {
        "source_commit": BEHAVIOR_COMMIT,
        "passed": True,
        "frames": 1,
        "camera_calibration": {
            camera: {
                "source": "native_camera_calibration",
                "intrinsic_matrix": [[300, 0, 200], [0, 300, 200], [0, 0, 1]],
            }
            for camera in CAMERAS
        },
    }
    (tmp_path / "sequence.json").write_text(json.dumps(metadata))
    (tmp_path / "observations.jsonl").write_text(json.dumps(raw) + "\n")
    return raw


def test_source_backed_proprio_order():
    decoded = decode_proprio(list(range(61)))
    assert decoded["joint_positions"] == list(range(3, 10)) + list(range(28, 35)) + list(
        range(53, 57)
    )
    assert decoded["gripper_positions"] == [24, 25, 49, 50]
    assert len(decoded["joint_velocities"]) == 18
    with pytest.raises(ValueError):
        decode_proprio([0] * 60)


def test_replay_requires_explicit_simulation_time(tmp_path):
    archive(tmp_path)
    frame = list(read_archive(tmp_path))[0]
    assert "sim_time" not in frame.envelope
    assert frame.captured_wall == 100
    assert frame.at_sim_time(2).sim_time == 2
    assert audit_archive(tmp_path)["new_native_actions"] == 0


@pytest.mark.parametrize("mutation", ["stamp", "time", "path", "proprio", "duplicate"])
def test_bad_recordings_rejected(tmp_path, mutation):
    raw = archive(tmp_path)
    if mutation == "stamp":
        raw["rgb"]["head"]["stamp"] = {"session": "foreign", "epoch": 0, "sequence": 0}
    elif mutation == "time":
        raw["rgb"]["head"]["observed_at"] = 99
    elif mutation == "path":
        raw["rgb"]["head"]["uri"] = "../secret.png"
    elif mutation == "proprio":
        raw["proprio"][0] = float("nan")
    content = json.dumps(raw) + "\n"
    (tmp_path / "observations.jsonl").write_text(content * (2 if mutation == "duplicate" else 1))
    with pytest.raises(ValueError):
        list(read_archive(tmp_path))


def test_unallowlisted_fields_never_exported(tmp_path):
    raw = archive(tmp_path)
    raw.update(score=1, global_pose=[1, 2, 3], camera_pose=[1, 2, 3])
    (tmp_path / "observations.jsonl").write_text(json.dumps(raw) + "\n")
    frame = list(read_archive(tmp_path))[0]
    assert not {"score", "global_pose", "camera_pose"} & frame.envelope.keys()
