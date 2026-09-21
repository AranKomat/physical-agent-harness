import numpy as np
import pytest

from experiments.behavior.base_hold import base_hold, settled
from physical_harness.hybrid_v0.classical import BodyTwist


def sample():
    p = np.zeros(61)
    p[3:10] = np.arange(7) / 10
    p[28:35] = -np.arange(7) / 10
    p[53:57] = [1, -1.4, -.5, .1]
    p[24:26], p[49:51] = .04, .02
    return p


def encode(p, twist=BodyTwist(0, 0, 0)):
    return np.asarray(base_hold(p, twist, gripper_ranges=((0, .05), (0, .05))))


def test_absolute_holds_and_smooth_gripper_inverse():
    p = sample()
    a = encode(p, BodyTwist(.03, -.02, .05))
    np.testing.assert_allclose(a[:3], [.04, -.02/.75, .05])
    np.testing.assert_array_equal(a[3:7], p[53:57])
    np.testing.assert_array_equal(a[7:14], p[3:10])
    np.testing.assert_array_equal(a[15:22], p[28:35])
    np.testing.assert_allclose(a[[14, 22]], [.6, -.2])
    assert not np.all(encode(p) == 0)


@pytest.mark.parametrize("index,value", [(0, float("nan")), (24, .1), (25, .03)])
def test_bad_feedback_is_rejected_not_clipped(index, value):
    p = sample()
    p[index] = value
    with pytest.raises(ValueError):
        encode(p)


@pytest.mark.parametrize("twist", [BodyTwist(.06, 0, 0), BodyTwist(.04, .04, 0), BodyTwist(0, 0, .2)])
def test_velocity_envelope_is_bounded(twist):
    with pytest.raises(ValueError):
        encode(sample(), twist)


@pytest.mark.parametrize("index", [0, 2, 10, 26, 35, 51, 57])
def test_settle_gate_checks_all_moving_groups(index):
    p = sample()
    assert settled(p)
    p[index] = .1
    assert not settled(p)


def test_malformed_width_and_gripper_ranges_fail():
    with pytest.raises(ValueError):
        encode(np.zeros(23))
    with pytest.raises(ValueError):
        base_hold(sample(), BodyTwist(0, 0, 0), gripper_ranges=((.05, 0), (0, .05)))
