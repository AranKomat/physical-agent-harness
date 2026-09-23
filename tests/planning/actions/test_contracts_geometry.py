from dataclasses import replace

import numpy as np
import pytest

from experiments.fixtures.actions import Fixture
from physical_harness.core.action_serde import (
    cloud_from_dict,
    gripper_from_dict,
    proposal_from_dict,
)
from physical_harness.core.actions import Pose, number, plain, strict_loads
from physical_harness.perception.geometry import (
    Intrinsics,
    compose_tcp,
    deproject_masked_depth,
    fit_surface,
    pose_from_approach,
)


@pytest.mark.parametrize("value", [True, False, float('nan'), float('inf'), '1', None, [], {}])
def test_nonfinite_or_coerced_number_rejected(value):
    with pytest.raises(ValueError):
        number(value)


@pytest.mark.parametrize("payload", ['{"a":1,"a":2}', '{"a":NaN}', '[]', 'null', '{"a":Infinity}'])
def test_strict_json(payload):
    with pytest.raises(ValueError):
        strict_loads(payload)


@pytest.mark.parametrize("kind", ['reflection', 'nonorthogonal', 'homogeneous', 'nonfinite', 'mutable'])
def test_bad_pose(kind):
    m = list(Pose('map').matrix)
    if kind == 'reflection':
        m[0] = -1
    if kind == 'nonorthogonal':
        m[1] = .1
    if kind == 'homogeneous':
        m[15] = 2
    if kind == 'nonfinite':
        m[3] = float('nan')
    with pytest.raises(ValueError):
        Pose('map', m if kind == 'mutable' else tuple(m))


@pytest.mark.parametrize("field,value", [('episode', 'other'), ('execution_epoch', 1), ('frame_epoch', 'other'),
                                        ('robot_fingerprint', 'other'), ('calibration_fingerprint', 'other'),
                                        ('domain', 'behavior_sim'), ('frame', 'other')])
def test_basis_change_invalidates_continuity(field, value):
    b = Fixture().current
    with pytest.raises(PermissionError):
        b.require_continuity(replace(b, **{field: value}))


@pytest.mark.parametrize("now", [99., 103.])
def test_capture_freshness(now):
    with pytest.raises(PermissionError):
        Fixture().current.fresh(now, 2.)


def test_geometry_and_gripper_json_roundtrip():
    f = Fixture()
    c = f.cloud()
    assert cloud_from_dict(plain(c)) == c
    assert gripper_from_dict(plain(f.gripper)) == f.gripper
    for a in f.catalog().actions:
        p = a.program.proposal
        assert proposal_from_dict(plain(p)) == p


def project(depth=None, mask=None, convention='optical_z', transform=None, **kwargs):
    f = Fixture()
    d = np.full((16, 16), 800.) if depth is None else depth
    m = np.ones((16, 16), dtype=bool) if mask is None else mask
    return deproject_masked_depth(basis=f.current, depth=d, mask=m,
                                  intrinsics=Intrinsics(16, 16, 100., 100., 7.5, 7.5, .001, convention),
                                  camera_to_frame=transform or Pose('fixture_map'), entity='obj', part='part',
                                  source_camera='head', evidence_ids=('rgb', 'depth'), semantic_confidence=.8,
                                  **kwargs)


def test_optical_depth_metric_and_no_input_mutation():
    depth = np.full((16, 16), 800.)
    mask = np.ones((16, 16), dtype=bool)
    c = project(depth, mask)
    assert all(p[2] == pytest.approx(.8) for p in c.points)
    assert np.all(depth == 800.) and mask.all()
    assert c.centroid == pytest.approx((0, 0, .8))


def test_ray_depth_is_not_axial_depth():
    c = project(convention='ray_range')
    assert all(np.linalg.norm(p) == pytest.approx(.8) for p in c.points)
    assert c.points[0][2] < .8


@pytest.mark.parametrize("bad", [np.zeros((16, 16)), np.full((16, 16), np.nan), np.full((16, 16), np.inf),
                                  np.ones((15, 16)), np.ones((16, 16), dtype=bool)])
def test_invalid_depth_rejected(bad):
    with pytest.raises(ValueError):
        project(depth=bad)


def test_fraction_and_downsampling_explicit():
    d = np.full((16, 16), 800.)
    d[:4] = 0
    c = project(depth=d, max_points=32)
    assert len(c.points) == 32 and c.valid_fraction == .75
    with pytest.raises(ValueError):
        project(depth=d, minimum_valid_fraction=.9)


def test_nonbinary_masks_cannot_smuggle_simulator_labels():
    with pytest.raises(ValueError):
        project(mask=np.ones((16, 16), dtype=np.int32))


def test_frame_transform_and_surface_normal():
    c = project()
    s = fit_surface(c)
    assert s.outward_normal == pytest.approx((0, 0, -1))
    assert s.residual_p95_m < 1e-10
    p = pose_from_approach('fixture_map', s.point, tuple(-v for v in s.outward_normal))
    assert p.approach == pytest.approx((0, 0, 1))


def test_degenerate_surface_not_a_contact_target():
    c = Fixture().cloud()
    collinear = replace(c, points=tuple((i*.01, 0., .8) for i in range(20)))
    with pytest.raises(ValueError):
        fit_surface(collinear)


def test_grasp_tcp_transform_is_composed_once_not_inverted():
    grasp = pose_from_approach('map', (1., 2., 3.), (1., 0., 0.))
    shift = Pose('grasp').shifted((0., 0., 1.), .1)
    tcp = compose_tcp(grasp, shift)
    assert tcp.xyz == pytest.approx((1.1, 2, 3))
    with pytest.raises(ValueError):
        compose_tcp(grasp, Pose('map'))


def test_invalid_gripper_joint_targets():
    f = Fixture()
    with pytest.raises(ValueError):
        replace(f.gripper, closed_positions=(1.,))


def test_json_size_limit_counts_utf8_bytes():
    from physical_harness.core.actions import strict_loads
    with pytest.raises(ValueError, match='Bounded'):
        strict_loads('{"value":"'+'界'*40+'"}', max_bytes=100)
