import json
import subprocess
import sys

import pytest

from physical_harness.core.events import EventBus, EventType
from physical_harness.execution.graph_bridge import publish_monitor_event
from physical_harness.perception.identity import IdentityLedger
from physical_harness.reasoning.monitors import MonitorSignal
from physical_harness.world.state import WorldState
from tests.planning.tasks.test_identity import claim, track


def test_identity_projection_preserves_raw_perception(journal):
    ledger = IdentityLedger(journal)
    entity = ledger.new_entity(track(), claim())
    with WorldState(':memory:', 'fixture') as world:
        world.add_evidence('source', 0.0, 'perception', 'fixture/frame')
        world.update(entity, 'label', 'ambiguous-side-view', 'source')
        ledger.project_world(world, entity, 'source')
        assert world.belief(entity, 'label')['object'] == 'ambiguous-side-view'
        canonical = world.belief(entity, 'canonical_semantics')
        assert canonical['epistemic'] == 'inferred'
        assert json.loads(canonical['object'])['label'] == 'radio'
        assert json.loads(world.belief(entity, 'identity_conflicts')['object']) == []


def test_identity_projection_rejects_foreign_episode(journal):
    ledger = IdentityLedger(journal)
    entity = ledger.new_entity(track(), claim())
    with WorldState(':memory:', 'different-episode') as world:
        with pytest.raises(PermissionError, match='Foreign WorldState'):
            ledger.project_world(world, entity, 'source')


@pytest.mark.parametrize('kind,expected', [
    ('target_lost', EventType.TARGET_LOST),
    ('skill_failed', EventType.SKILL_FAILED),
    ('verifier_uncertain', EventType.VERIFIER_UNCERTAIN),
    ('subgoal_complete', EventType.DECISION_REQUIRED),
    ('progress', None),
    ('completion_candidate', None),
])
def test_monitor_bridge_only_publishes_advisory_events(basis, kind, expected):
    bus = EventBus()
    received = []
    bus.subscribe(received.append)
    signal = MonitorSignal('signal', 'command', basis, kind, kind, basis.evidence_ids)
    event = publish_monitor_event(signal, bus)
    if expected is None:
        assert event is None and not bus.recent() and not received
    else:
        assert event.type == expected
        assert event.type != EventType.SKILL_VERIFIED
        assert event.episode_id == basis.episode and event.sim_time == basis.sim_time
        assert event.payload['semantic_authority'] == 'advisory_only'
        assert bus.recent() == received == [event]


def test_clean_import_does_not_load_inference_or_simulation():
    subprocess.run(
        [sys.executable, '-c',
         'import sys; import physical_harness.planning.tasks; '
         'assert not {"torch", "sam3", "omnigibson", "openai"}.intersection(sys.modules)'],
        check=True, capture_output=True, text=True, timeout=20,
    )
