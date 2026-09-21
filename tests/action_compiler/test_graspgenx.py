from dataclasses import replace

import numpy as np
import pytest

from physical_harness.action_compiler.fixture import Fixture
from physical_harness.action_compiler.graspgenx import (
    AUDITED_REVISION,
    GraspGenXAdapter,
    LocalAssets,
    load_local,
    verify_files,
)
from physical_harness.action_compiler.types import Pose


def adapter(f, infer, allowed=True):
    return GraspGenXAdapter(object(), f.gripper, infer=infer, revision=AUDITED_REVISION,
                           model_digest='weights', gripper_name='fixture-jaw', allow_inference=allowed,
                           clock=f.clock)


def test_exact_audited_api_single_attempt_and_frame_conversion():
    f = Fixture()
    f.gripper = replace(f.gripper, grasp_to_tcp=Pose('grasp').shifted((0., 0., 1.), .1))
    called = []
    def infer(points, sampler, **kwargs):
        called.append(kwargs)
        assert points.dtype == np.float32 and points.shape[1] == 3
        poses = np.tile(np.eye(4), (2, 1, 1))
        poses[:, :3, 3] = (1, 2, 3)
        return poses, np.array([.4, .8])
    proposals = adapter(f, infer).propose(f.cloud(), deadline=110, top_k=2)
    assert called[0]['max_tries'] == 1 and called[0]['min_grasps'] == 1
    assert called[0]['remove_outliers'] is False
    assert proposals[0].parameters.pose.xyz == pytest.approx((1, 2, 3.1))
    assert proposals[0].score == .8 and 'uncalibrated' in proposals[0].score_kind
    assert proposals[0].gripper_fingerprint == f.gripper.fingerprint


@pytest.mark.parametrize('case', ['disabled', 'deadline'])
def test_no_accidental_model_execution(case):
    f = Fixture()
    def never(*args, **kwargs):
        raise AssertionError('must not infer')
    a = adapter(f, never, allowed=case != 'disabled')
    with pytest.raises((PermissionError, TimeoutError)):
        a.propose(f.cloud(), deadline=90 if case == 'deadline' else 110)


@pytest.mark.parametrize('case', ['nan', 'reflection', 'shape', 'scores', 'too_many'])
def test_invalid_model_outputs_rejected(case):
    f = Fixture()
    poses, scores = np.tile(np.eye(4), (2, 1, 1)), np.array([.5, .8])
    if case == 'nan':
        poses[0, 0, 0] = np.nan
    if case == 'reflection':
        poses[0, 0, 0] = -1
    if case == 'shape':
        poses = poses[:, :3, :3]
    if case == 'scores':
        scores = np.zeros((2, 1))
    if case == 'too_many':
        poses, scores = np.tile(np.eye(4), (100, 1, 1)), np.zeros(100)
    with pytest.raises(ValueError):
        adapter(f, lambda *a, **k: (poses, scores)).propose(f.cloud(), deadline=110, top_k=2)


def test_empty_grasps_not_fabricated():
    f = Fixture()
    assert adapter(f, lambda *a, **k: ([], [])).propose(f.cloud(), deadline=110) == ()


def test_late_grasp_results_discarded():
    f = Fixture()
    def infer(*args, **kwargs):
        f.now += 100
        return np.tile(np.eye(4), (1, 1, 1)), np.array([.9])
    a = adapter(f, infer)
    with pytest.raises(TimeoutError):
        a.propose(f.cloud(), deadline=110)
    assert a.calls == 1 and a.wall_s == 100


def test_live_loading_requires_explicit_permissions_before_paths_or_import(tmp_path):
    f = Fixture()
    assets = LocalAssets(tmp_path, tmp_path, tmp_path, tmp_path, 'gripper', 'g.pth', 'd.pth')
    with pytest.raises(PermissionError):
        load_local(assets, f.gripper, checkpoint_manifest={}, gripper_manifest={},
                   expected_gripper_fingerprint=f.gripper.fingerprint)


def test_manifest_integrity_lfs_and_traversal(tmp_path):
    import hashlib
    p = tmp_path/'x'
    p.write_bytes(b'payload')
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    verify_files(tmp_path, {'x': h})
    with pytest.raises(ValueError):
        verify_files(tmp_path, {'x': '0'*64})
    with pytest.raises(ValueError):
        verify_files(tmp_path, {'../escape': h})
    p.write_bytes(b'version https://git-lfs.github.com/spec/v1\n')
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='LFS'):
        verify_files(tmp_path, {'x': h})


def test_importing_adapter_does_not_import_upstream():
    import subprocess
    import sys
    command = 'import sys; import physical_harness.action_compiler.graspgenx; assert "graspgenx" not in sys.modules; assert "torch" not in sys.modules'
    subprocess.run([sys.executable, '-c', command], check=True, timeout=10)


def local_asset_fixture(tmp_path, f):
    import hashlib

    from physical_harness.action_compiler.types import digest
    source = tmp_path/'source'
    weights = tmp_path/'weights'
    gripper_root = tmp_path/'gripper-root'
    assets_dir = gripper_root/'assets'
    source.mkdir()
    (source/'marker').write_text('mock-source')
    manifests = []
    for root, files in ((weights, ('gen/config.yaml', 'dis/config.yaml', 'gen/g.pth', 'dis/d.pth')),
                        (assets_dir, ('x_grippers/jaw/config.json', 'x_grippers/jaw/gripper.urdf'))):
        manifest = {}
        for rel in files:
            p = root/rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'authorized-test-fixture-'+rel.encode())
            manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        manifests.append(manifest)
    f.gripper = replace(f.gripper, asset_digest=digest(manifests[1]))
    return LocalAssets(source, weights, gripper_root, assets_dir, 'jaw', 'g.pth', 'd.pth'), manifests


def test_loader_validates_everything_before_mock_upstream_import(tmp_path, monkeypatch):
    import os
    import sys
    import types

    import physical_harness.action_compiler.graspgenx as module
    f = Fixture()
    assets, (weights, grippers) = local_asset_fixture(tmp_path, f)
    monkeypatch.setattr(module.subprocess, 'check_output',
                        lambda command, **kwargs: AUDITED_REVISION if 'rev-parse' in command else '')
    monkeypatch.setattr(sys, 'path', list(sys.path))
    monkeypatch.setattr(os, 'environ', dict(os.environ))
    imported = []
    class Sampler:
        def __init__(self, cfg, name, **kwargs):
            assert name == 'jaw' and kwargs['use_tensorrt'] is False
        @staticmethod
        def run_inference(*args, **kwargs):
            raise AssertionError('Loading does not run inference')
    def load(name):
        assert os.environ['GRASPGENX_CHECKPOINT_DIR'] == str(assets.checkpoint_root)
        assert os.environ['GRASPGENX_GRIPPER_CFG_DIR'] == str(assets.gripper_root)
        imported.append(name)
        if name.endswith('grasp_server'):
            return types.SimpleNamespace(GraspGenXSampler=Sampler)
        return types.SimpleNamespace(load_model_cfg=lambda *args: ('mock-config', args))
    monkeypatch.setattr(module.importlib, 'import_module', load)
    a = load_local(assets, f.gripper, checkpoint_manifest=weights, gripper_manifest=grippers,
                   expected_gripper_fingerprint=f.gripper.fingerprint,
                   allow_inference=True, licenses_accepted=True)
    assert a.calls == 0 and len(imported) == 2


@pytest.mark.parametrize('problem', ['dirty', 'revision', 'manifest', 'gripper_identity', 'incomplete_meshes'])
def test_local_loader_refuses_unverified_environment_before_import(tmp_path, monkeypatch, problem):
    import physical_harness.action_compiler.graspgenx as module
    f = Fixture()
    assets, (weights, grippers) = local_asset_fixture(tmp_path, f)
    def git(command, **kwargs):
        if 'rev-parse' in command:
            return 'wrong' if problem == 'revision' else AUDITED_REVISION
        return 'modified source' if problem == 'dirty' else ''
    monkeypatch.setattr(module.subprocess, 'check_output', git)
    def never(name):
        raise AssertionError('No upstream import on failed local preflight')
    monkeypatch.setattr(module.importlib, 'import_module', never)
    if problem == 'manifest':
        weights['gen/g.pth'] = '0'*64
    if problem == 'incomplete_meshes':
        grippers.pop('x_grippers/jaw/gripper.urdf')
    with pytest.raises((PermissionError, ValueError)):
        load_local(assets, f.gripper, checkpoint_manifest=weights, gripper_manifest=grippers,
                   expected_gripper_fingerprint='wrong' if problem == 'gripper_identity' else f.gripper.fingerprint,
                   allow_inference=True, licenses_accepted=True)
