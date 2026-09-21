from types import SimpleNamespace

import numpy as np
import pytest

from experiments.behavior.contracts import Evidence, Observation, Stamp
from experiments.behavior.observations import CAMERAS, capture_intrinsics


def fixture():
    stamp = Stamp(session="intrinsics", epoch=0, sequence=7)
    refs = {kind: {name: Evidence(id=f"{name}-{kind}", stamp=stamp,
                                observed_at=2., source=kind, uri=f"{name}.{kind}")
                   for name in CAMERAS} for kind in ("rgb", "depth")}
    obs = Observation(stamp=stamp, observed_at=2., proprio=(0.,) * 61, **refs)
    sensors = {prefix.split("::", 1)[1]: SimpleNamespace(intrinsic_matrix=np.eye(3))
               for prefix in CAMERAS.values()}
    evaluator = SimpleNamespace(robot_camera_names=dict(CAMERAS),
                                robot=SimpleNamespace(sensors=sensors))
    return evaluator, obs


def test_intrinsics_capture_binds_evidence_and_does_not_read_world_pose():
    evaluator, obs = fixture()
    result = capture_intrinsics(evaluator, obs)
    for camera, record in result.items():
        assert record["stamp"] == obs.stamp.model_dump()
        assert record["observed_at"] == 2.
        assert record["rgb_evidence_id"] == obs.rgb[camera].id
        assert record["depth_evidence_id"] == obs.depth[camera].id
        assert record["extrinsics"] is None


@pytest.mark.parametrize("mutation", ["mapping", "stamp", "time", "matrix"])
def test_invalid_calibration_rejected(mutation):
    evaluator, obs = fixture()
    if mutation == "mapping":
        evaluator.robot_camera_names["head"] = "other::camera"
    elif mutation == "stamp":
        obs.depth["head"] = obs.depth["head"].model_copy(
            update={"stamp": obs.stamp.model_copy(update={"sequence": 8})})
    elif mutation == "time":
        obs.depth["head"] = obs.depth["head"].model_copy(update={"observed_at": 3.})
    else:
        evaluator.robot.sensors[CAMERAS["head"].split("::", 1)[1]].intrinsic_matrix[0, 0] = 0
    with pytest.raises(ValueError):
        capture_intrinsics(evaluator, obs)
