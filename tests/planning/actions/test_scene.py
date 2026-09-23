from dataclasses import replace

import pytest

from experiments.fixtures.actions import Fixture
from physical_harness.perception.scene import SceneView


def test_current_scene_preserves_parts_and_evidence_without_exposing_point_cloud():
    f = Fixture()
    original = f.current
    catalog = f.catalog()
    view = SceneView(f.current, (f.cloud(), f.cloud('button')), catalog).view()
    assert f.current == original
    assert len(view['entities']) == 1
    parts = view['entities'][0]['observed_parts']
    assert {p['part'] for p in parts} == {'whole', 'button'}
    assert all(p['geometry_scope'] == 'partial_observed_surface_only' for p in parts)
    assert all('points' not in p for p in parts)
    assert view['interaction_catalog']['catalog_id'] == catalog.id
    assert 'task_success' not in view


@pytest.mark.parametrize('change', ['epoch', 'geometry', 'observation'])
def test_scene_refuses_mixed_source_revisions(change):
    f = Fixture()
    cloud = f.cloud()
    field = {'epoch': 'execution_epoch', 'geometry': 'geometry_revision', 'observation': 'observation_id'}[change]
    basis = replace(f.current, **{field: 1 if field == 'execution_epoch' else 'changed'})
    with pytest.raises(PermissionError):
        SceneView(f.current, (replace(cloud, basis=basis),), f.catalog())


def test_empty_view_and_budget_are_explicit():
    f = Fixture()
    scene = SceneView(f.current, (), f.catalog())
    assert scene.view()['entities'] == []
    with pytest.raises(ValueError, match='budget'):
        scene.view(max_bytes=100)
