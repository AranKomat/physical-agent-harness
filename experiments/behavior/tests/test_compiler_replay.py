import json

import numpy as np
import pytest

from experiments.behavior.compiler_replay import main, read_capture, replay_run
from experiments.behavior.contracts import Stamp
from experiments.behavior.observations import EvidenceStore

CAMERAS = ("head", "left_wrist", "right_wrist")


def _capture(store, *, session="replay", sequence=0, observed_at=10.0):
    stamp = Stamp(session=session, epoch=0, sequence=sequence)
    rgb, depth, calibration = {}, {}, {}
    for offset, camera in enumerate(CAMERAS):
        color = np.full((6, 8, 3), 20 + offset, dtype=np.uint8)
        distance = np.full((6, 8), 1.0 + offset / 10, dtype=np.float32)
        rgb[camera] = store.put(color, "rgb", stamp, observed_at).model_dump()
        depth[camera] = store.put(distance, "depth", stamp, observed_at).model_dump()
        calibration[camera] = {
            "intrinsic_matrix": [[4.0, 0.0, 4.0], [0.0, 4.0, 3.0], [0.0, 0.0, 1.0]],
            "image_shape": [6, 8],
            "source": "native_camera_intrinsics",
            "extrinsics": None,
            "stamp": stamp.model_dump(),
            "observed_at": observed_at,
            "rgb_evidence_id": rgb[camera]["id"],
            "depth_evidence_id": depth[camera]["id"],
        }
    return {
        "calibration": calibration,
        "observation": {
            "stamp": stamp.model_dump(),
            "observed_at": observed_at,
            "rgb": rgb,
            "depth": depth,
            "proprio": [0.0] * 61,
        },
    }


def _run(tmp_path, captures):
    run = tmp_path / "A"
    store = EvidenceStore(run / "evidence")
    materialized = [capture(store, sequence=i) if callable(capture) else capture
                    for i, capture in enumerate(captures)]
    (run / "hybrid_short.json").write_text(json.dumps({"captures": materialized}))
    return run, materialized


def _annotation(capture, *, part="visible_body_patch", evidence_id=None):
    return {
        "camera": "head",
        "rgb_evidence_id": evidence_id or capture["observation"]["rgb"]["head"]["id"],
        "inspected": True,
        "method": "annotation_assisted_rectangle",
        "entity": "radio",
        "part": part,
        "box_xyxy": [2, 1, 6, 5],
        "note": "Visible radio body patch inspected in retained RGB.",
    }


def test_absent_and_explicitly_empty_annotations_stay_in_denominator(tmp_path):
    run, captures = _run(tmp_path, [lambda store, sequence: _capture(
        store, sequence=sequence) for _ in range(2)])

    report = replay_run(run, annotations={"0": []})

    assert report["denominator"] == report["processed"] == 2
    assert len(report["captures"]) == 2
    assert sum(report["summary"]["status_counts"].values()) == 2
    assert report["captures"][0]["status"] == "empty"
    assert report["captures"][1]["status"] == "unannotated"
    assert report["summary"]["geometry_count"] == 0
    assert report["summary"]["real_qualified_candidates"] == 0


def test_annotation_produces_camera_geometry_but_no_qualified_action(tmp_path):
    run, captures = _run(tmp_path, [lambda store, sequence: _capture(
        store, sequence=sequence)])

    report = replay_run(run, annotations={"0": [_annotation(captures[0])]})

    assert report["denominator"] == report["processed"] == 1
    assert report["summary"]["geometry_count"] == 1
    assert report["summary"]["eligible_actions"] == 0
    assert report["summary"]["real_qualified_candidates"] == 0
    geometry = report["captures"][0]["geometry"][0]
    assert geometry["annotation_assisted"] is True
    assert geometry["frame"].startswith("optical:head:")
    assert geometry["point_count"] == 16
    catalogs = report["captures"][0]["contract_probe_catalog"]
    assert catalogs
    actions = [action for catalog in catalogs.values() for action in catalog["actions"]]
    assert actions and all(not action["eligible"] for action in actions)
    assert all(action["blocked_by"] for action in actions)
    assert all(action["parameter_count_exposed_to_model"] == 0 for action in actions)
    stage = next(action for action in actions if action["intent"]["verb"] == "stage")
    assert {"ik", "gripper_compatibility", "swept_collision"} <= set(stage["blocked_by"])
    programs = [entry for camera in report["captures"][0]["cameras"]
                for entry in camera.get("programs_and_reviews", [])]
    assert programs
    assert all(check["passed"] is None
               for entry in programs for check in entry["review"]["checks"])


@pytest.mark.parametrize("mutation", ["content", "identity", "calibration", "path"])
def test_read_capture_rejects_broken_evidence_provenance(tmp_path, mutation):
    run, captures = _run(tmp_path, [lambda store, sequence: _capture(
        store, sequence=sequence)])
    depth = captures[0]["observation"]["depth"]["head"]
    if mutation == "content":
        (run / "evidence" / depth["uri"]).write_bytes(b"tampered")
        match = "hash"
    elif mutation == "identity":
        depth["id"] = "0" * 64
        captures[0]["calibration"]["head"]["depth_evidence_id"] = depth["id"]
        match = "identity"
    elif mutation == "calibration":
        captures[0]["calibration"]["head"]["depth_evidence_id"] = "0" * 64
        match = "binding"
    else:
        depth["uri"] = "../escaped.npy"
        match = "escapes"

    with pytest.raises(ValueError, match=match):
        read_capture(captures[0], run / "evidence", "head")


@pytest.mark.parametrize("mutation", ["evidence", "part", "bounds", "inspected"])
def test_invalid_annotation_is_retained_as_error_not_fallback_mask(tmp_path, mutation):
    run, captures = _run(tmp_path, [lambda store, sequence: _capture(
        store, sequence=sequence)])
    annotation = _annotation(captures[0])
    if mutation == "evidence":
        annotation["rgb_evidence_id"] = "different-capture"
    elif mutation == "part":
        annotation["part"] = "power_button"
    elif mutation == "bounds":
        annotation["box_xyxy"] = [0, 0, 80, 60]
    else:
        annotation["inspected"] = False

    report = replay_run(run, annotations={"0": [annotation]})

    assert report["denominator"] == report["processed"] == 1
    assert len(report["captures"]) == 1
    assert report["captures"][0]["status"] == "error"
    assert report["captures"][0]["geometry"] == []
    assert report["summary"]["geometry_count"] == 0
    assert report["summary"]["eligible_actions"] == 0


def test_malformed_capture_is_counted_and_does_not_abort_replay(tmp_path):
    run, captures = _run(tmp_path, [lambda store, sequence: _capture(
        store, sequence=sequence), lambda store, sequence: _capture(
            store, sequence=sequence)])
    del captures[0]["observation"]["depth"]["head"]
    (run / "hybrid_short.json").write_text(json.dumps({"captures": captures}))

    report = replay_run(run)

    assert report["denominator"] == report["processed"] == 2
    assert len(report["captures"]) == 2
    assert report["captures"][0]["status"] == "error"
    assert report["captures"][1]["status"] == "unannotated"
    assert sum(report["summary"]["status_counts"].values()) == 2


def test_partial_invalid_depth_is_finite_json_and_source_is_unchanged(tmp_path):
    def partial_depth(store, sequence):
        capture = _capture(store, sequence=sequence)
        stamp = Stamp.model_validate(capture["observation"]["stamp"])
        depth = np.ones((6, 8), dtype=np.float32)
        depth[0, 0] = np.nan
        depth[0, 1] = np.inf
        ref = store.put(depth, "depth", stamp, capture["observation"]["observed_at"])
        capture["observation"]["depth"]["head"] = ref.model_dump()
        capture["calibration"]["head"]["depth_evidence_id"] = ref.id
        return capture

    run, _ = _run(tmp_path, [partial_depth])
    before = {path.relative_to(run): path.read_bytes()
              for path in run.rglob("*") if path.is_file()}

    report = replay_run(run)

    encoded = json.dumps(report, allow_nan=False)
    assert encoded
    head = report["captures"][0]["cameras"][0]
    assert head["status"] == "ok"
    assert head["observed_geometry"]["point_count"] == 46
    assert head["depth_range_m"] == [1.0, 1.0]
    after = {path.relative_to(run): path.read_bytes()
             for path in run.rglob("*") if path.is_file()}
    assert after == before


def test_cli_rejects_output_inside_retained_source_run(tmp_path):
    run, _ = _run(tmp_path, [lambda store, sequence: _capture(
        store, sequence=sequence)])
    output = run / "compiler_replay_forbidden.json"

    with pytest.raises(SystemExit, match="2"):
        main(["--run-dir", str(run), "--output", str(output)])

    assert not output.exists()
