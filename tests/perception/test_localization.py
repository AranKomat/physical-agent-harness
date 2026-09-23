import pytest

from physical_harness.integrations.sensors.behavior import LegalObservation
from physical_harness.perception.localization import LocalizationLost, RGBDOdometry

np = pytest.importorskip("numpy")


def observation(at, episode="episode"):
    return LegalObservation.from_envelope(
        {
            "schema_version": 1,
            "episode_id": episode,
            "observation_id": f"frame-{at}",
            "sim_time": at,
            "rgb_refs": {"head": f"rgb-{at}"},
            "depth_refs": {"head": f"depth-{at}"},
            "proprioception": {"joint_positions": [0.0]},
            "camera_frames": {"head": "head_optical"},
            "camera_intrinsics": {
                "head": {
                    "width": 8,
                    "height": 6,
                    "fx": 10,
                    "fy": 10,
                    "cx": 4,
                    "cy": 3,
                    "depth_scale_m": 1,
                }
            },
        }
    )


def artifacts(ref):
    if ref.startswith("rgb"):
        return np.zeros((6, 8, 3), dtype=np.uint8)
    return np.ones((6, 8), dtype=np.float32)


def test_rgbd_odometry_composes_legal_relative_motion():
    delta = np.eye(4)
    delta[0, 3] = 0.1

    def estimate(previous_rgb, previous_depth, rgb, depth, calibration):
        assert previous_rgb.shape == rgb.shape == (6, 8, 3)
        assert previous_depth.shape == depth.shape == (6, 8)
        assert calibration["fx"] == 10
        return True, delta, np.eye(6) * 20

    odometry = RGBDOdometry(artifacts, motion_estimator=estimate, min_information=10)
    first = odometry(observation(0))
    second = odometry(observation(1))
    assert first["evidence_ids"] == ["frame-0"]
    assert second["evidence_ids"] == ["frame-0", "frame-1"]
    assert second["transform"][0][3] == pytest.approx(-0.1)
    assert second["confidence"] == 1
    envelope = observation(1).to_envelope()
    envelope["estimated_pose"] = second
    LegalObservation.from_envelope(envelope)


@pytest.mark.parametrize("failure", ["jump", "information", "backend"])
def test_rgbd_odometry_latches_loss(failure):
    delta, information, success = np.eye(4), np.eye(6) * 20, True
    if failure == "jump":
        delta[0, 3] = 1
    elif failure == "information":
        information[0, 0] = 0
    else:
        success = False
    odometry = RGBDOdometry(
        artifacts,
        motion_estimator=lambda *_: (success, delta, information),
        min_information=10,
    )
    odometry(observation(0))
    with pytest.raises(LocalizationLost):
        odometry(observation(1))
    with pytest.raises(LocalizationLost, match="new map"):
        odometry(observation(2))


def test_rgbd_odometry_rejects_gap_episode_and_bad_artifacts():
    odometry = RGBDOdometry(artifacts, motion_estimator=lambda *_: None)
    odometry(observation(0))
    with pytest.raises(ValueError, match="episode"):
        odometry(observation(1, "other"))

    odometry = RGBDOdometry(artifacts, motion_estimator=lambda *_: None, max_frame_gap_s=1)
    odometry(observation(0))
    with pytest.raises(LocalizationLost, match="gap"):
        odometry(observation(2))

    bad = RGBDOdometry(lambda _: [[0]])
    with pytest.raises(ValueError, match="calibration"):
        bad(observation(0))


def test_fixed_reference_does_not_accumulate_or_relax_current_frame_freshness():
    delta = np.eye(4)
    delta[0, 3] = .1
    tracker = RGBDOdometry(artifacts, reference_mode="first", max_frame_gap_s=1,
                          motion_estimator=lambda *_: (True, delta, np.eye(6) * 20))
    tracker(observation(0))
    for at in (1, 2, 3):
        result = tracker(observation(at))
        assert result["transform"][0][3] == pytest.approx(-.1)
        assert result["evidence_ids"] == ["frame-0", f"frame-{at}"]
    with pytest.raises(ValueError, match="stale"):
        tracker(observation(3))
    with pytest.raises(LocalizationLost, match="gap"):
        tracker(observation(5))
    with pytest.raises(LocalizationLost, match="new map"):
        tracker(observation(6))


@pytest.mark.parametrize("reference_mode", ["first", "previous"])
def test_reference_rejects_calibration_change(reference_mode):
    tracker = RGBDOdometry(artifacts, reference_mode=reference_mode)
    tracker(observation(0))
    envelope = observation(1).to_envelope()
    envelope["camera_intrinsics"]["head"]["fx"] = 11
    with pytest.raises(LocalizationLost, match="calibration changed"):
        tracker(LegalObservation.from_envelope(envelope))


def test_unknown_reference_mode_rejected():
    with pytest.raises(ValueError, match="reference mode"):
        RGBDOdometry(artifacts, reference_mode="silent_reset")
