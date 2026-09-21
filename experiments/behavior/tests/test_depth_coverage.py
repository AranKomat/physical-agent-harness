import numpy as np
import pytest

from experiments.behavior.depth_coverage import classify_depth_support


def camera(depth=2.):
    return np.eye(4), np.array([[2., 0, 3], [0, 2, 3], [0, 0, 1]]), np.full((7, 7), depth)


def test_classes_partition_samples():
    result = classify_depth_support([[0, 0, 1], [0, 0, 2], [0, 0, -1], [10, 0, 1]], [camera()])
    assert result == {"samples": 4, "outside_all_views": 2,
                      "in_view_without_valid_depth": 0,
                      "valid_depth_without_beyond_support": 1, "depth_beyond_sample": 1}


@pytest.mark.parametrize("value", [0., -1., float("nan"), float("inf")])
def test_bad_neighbor_does_not_support_free_sample(value):
    t, k, d = camera()
    d[2, 2] = value
    result = classify_depth_support([[0, 0, 1]], [(t, k, d)])
    assert result["in_view_without_valid_depth"] == 1
    assert result["depth_beyond_sample"] == 0


def test_nearest_neighbor_occlusion_and_margin():
    t, k, d = camera()
    d[2, 2] = 1.01
    result = classify_depth_support([[0, 0, 1]], [(t, k, d)])
    assert result["valid_depth_without_beyond_support"] == 1


def test_camera_union_and_rigid_transform_direction():
    t, k, d = camera()
    t[:3, :3] = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
    t[:3, 3] = [4, 1, 2]
    result = classify_depth_support([[5, 1, 2]], [camera(0.), (t, k, d)])
    assert result["depth_beyond_sample"] == 1
    assert result["outside_all_views"] == 0


def test_empty_camera_set_and_empty_points():
    assert classify_depth_support([[0, 0, 1]], [])["outside_all_views"] == 1
    assert classify_depth_support(np.empty((0, 3)), [camera()])["samples"] == 0


@pytest.mark.parametrize("points", [[[0, 0]], [[0, 0, float("nan")]]])
def test_invalid_points(points):
    with pytest.raises(ValueError):
        classify_depth_support(points, [camera()])


@pytest.mark.parametrize("part", ["transform", "intrinsic", "image", "margin"])
def test_invalid_geometry(part):
    t, k, d = camera()
    margin = .02
    if part == "transform":
        t[0, 0] = 2
    elif part == "intrinsic":
        k[0, 0] = 0
    elif part == "image":
        d = np.ones(7)
    else:
        margin = -1
    with pytest.raises(ValueError):
        classify_depth_support([[0, 0, 1]], [(t, k, d)], margin=margin)
