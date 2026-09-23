import subprocess
import sys
import time
from dataclasses import replace

import pytest

from experiments.fixtures.embodied import run_demo
from physical_harness.core.actions import Pose
from physical_harness.integrations.curobo import verify_curobo_checkout
from physical_harness.perception.discovery import AsyncDiscovery
from physical_harness.perception.discovery_coordinator import DiscoveryCoordinator
from physical_harness.perception.identity import (
    IdentityLedger,
    SemanticClaim,
    Tracklet,
    focus_identity_view,
)
from physical_harness.perception.keyframes import SemanticKeyframes, ViewSample
from physical_harness.planning.map_tools import MapTool, place_destination, rank_frontiers
from physical_harness.reasoning.executive import ExecutiveCadence
from physical_harness.world.inventory import SemanticInventory
from tests.reasoning.embodied.conftest import make_basis, make_frame, response
from tests.reasoning.embodied.test_maps_capabilities import grid


def test_combined_fixture_uses_real_journal_job_manager_and_action_executor(tmp_path):
    output = tmp_path / 'demo'
    report = run_demo(output)
    assert report['real_model_calls'] == report['native_robot_actions'] == 0
    assert report['synthetic_counted_steps'] == 1
    assert report['semantic_status'] == 'requires_external_verification'
    assert report['discovery_has_actuator_authority'] is False
    assert report['old_catalog_reused'] is False
    assert report['unresolved_robot_owners'] == 0
    assert (output / 'journal.sqlite').exists()
    with pytest.raises(FileExistsError):
        run_demo(output)

def test_map_as_tool_rejects_metric_reuse_and_unknown_destination():
    g = grid()
    destination = place_destination(g, 'kitchen', current_anchor=Pose('local').shifted((1.0, 0.0, 0.0), 0.5), evidence_ids=('place',))
    tool = MapTool(g, (destination,))
    proposed = tool.select(destination.id, current=g.basis, now=100)
    assert proposed['motion_authority'] is False and proposed['subject'] == 'kitchen'
    with pytest.raises(PermissionError):
        tool.select('invented', current=g.basis, now=100)
    with pytest.raises(PermissionError):
        tool.select(destination.id, current=replace(g.basis, geometry_revision='new'), now=100)
    with pytest.raises(PermissionError):
        MapTool(g, (replace(destination, map_fingerprint='wrong'),))

def test_frontier_choice_is_fresh_search_hint_not_target_geometry():
    g = grid()
    d = rank_frontiers(g)[0].destination
    out = MapTool(g, (d,)).select(d.id, current=g.basis, now=100)
    assert out['requires_reacquisition'] and (not out['motion_authority'])

@pytest.mark.parametrize('old_task', [False, True])
def test_async_diary_has_no_action_path_or_current_metric_writes(journal, old_task):
    now = [100.0]

    def invoke(r, d):
        raw = response(r)
        raw['updates'][0]['region_id'] = None
        raw['updates'][0]['box'] = [0.1, 0.1, 0.9, 0.9]
        return raw
    worker = AsyncDiscovery(journal=journal, invoke=invoke, model_name='mock', enabled=True, clock=lambda: now[0])
    inv = SemanticInventory(journal)
    cadence = ExecutiveCadence()
    coord = DiscoveryCoordinator(journal=journal, keyframes=SemanticKeyframes(), worker=worker, inventory=inv, executive_scheduler=cadence)
    f, _ = make_frame()
    coord.observe(ViewSample(f, (0.1, 0.2, 0.3)), now=100, task='Find radio', task_revision='old' if old_task else 'active')
    cutoff = time.monotonic() + 1
    while not worker.completed and time.monotonic() < cutoff:
        time.sleep(0.005)
    now[0] = 105
    got = coord.poll(current=f.basis, now=105, task_revision='active')
    assert len(got) == 1 and got[0]['native_actions'] == 0
    assert len(inv.records) == 1 and (not journal.records('compiled_action'))
    assert not journal.records('situated_identity')
    assert bool(cadence.due(now=105, active_task_revision='active')) is (not old_task)
    assert worker.close(1)

def test_current_identity_and_remembered_semantics_are_not_conflated(journal):
    identity = IdentityLedger(journal)
    b = make_basis()
    track = Tracklet(b, 'head', 's', '1', 'mask', (0.0, 0.0, 1.0), 0.02)
    entity = identity.new_entity(track, SemanticClaim('radio', 'recognized', b.evidence_ids, 'fixture'))
    assert focus_identity_view(identity, entity, b)['current_geometry_available']
    later = make_basis(1, wall=101, sim=1)
    view = focus_identity_view(identity, entity, later)
    assert not view['current_geometry_available']
    assert view['remembered_semantics']['label'] == 'radio'
    assert view['current_binding'] is None

def test_import_new_package_does_not_import_or_launch_models():
    script = 'import sys; import physical_harness.reasoning; assert not any(k in sys.modules for k in ["torch","curobo","sam3","transformers","mujoco"])'
    result = subprocess.run([sys.executable, '-c', script], text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr

def test_planner_loader_requires_explicit_local_checkout():
    with pytest.raises(PermissionError):
        verify_curobo_checkout(None, object())

def test_restart_replays_durable_semantics_not_provider_calls(journal):
    from physical_harness.perception.discovery import recover_completed_results
    from tests.reasoning.embodied.conftest import make_request
    calls = []
    worker = AsyncDiscovery(journal=journal, invoke=lambda r, d: calls.append(r.id) or response(r), model_name='mock', enabled=True, clock=lambda: 104)
    req = make_request()
    worker.submit(req)
    cutoff = time.monotonic() + 1
    while not worker.completed and time.monotonic() < cutoff:
        time.sleep(0.005)
    assert worker.close(1)
    recovered = recover_completed_results(journal)
    assert len(recovered) == 1 and calls == ['req']
    inventory = SemanticInventory(journal)
    inventory.accept(recovered[0], received_wall=110, current_task_revision='task-v1')
    assert recover_completed_results(journal, committed_request_ids=frozenset(inventory.completed)) == ()
    assert calls == ['req']
