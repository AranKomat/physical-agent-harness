from dataclasses import replace

import pytest

from physical_harness.situated.monitor import MonitorVerdict, ProgressMonitor, parse_monitor_reply
from physical_harness.situated.visual import (
    GoalKind,
    ObservationFrame,
    ReferenceGrant,
    VisualAsset,
    VisualGoal,
    VisualRole,
    monitor_packet,
)

from .conftest import make_basis


def asset(n, role=VisualRole.OBSERVATION, **kwargs):
    return replace(VisualAsset(f'img-{n}', 'fixture', role, 'head', n, n, 'a' * 64, (f'rgb-{n}',), 'cmd' if role == VisualRole.COMMAND_ANCHOR else None), **kwargs)

def packet(n=1, goal=None):
    frames = tuple((ObservationFrame(make_basis(k), asset(k)) for k in range(n + 1)))
    return monitor_packet(command_id='cmd', goal=goal or VisualGoal('g', GoalKind.INFORMATION, 'e', 'identity', 'new diagnostic view'), frames=frames, anchor=asset(0, VisualRole.COMMAND_ANCHOR, asset_id='anchor'))

def verdict(p, status='complete', revision='test'):
    return MonitorVerdict(p.fingerprint, status, (p.recent[-1].asset_id,), 'fake-monitor', revision)

def test_causal_window_stride_and_no_duplicate_padding():
    p = packet(10)
    assert [a.observed_at for a in p.recent] == [1, 4, 7, 10]
    assert len(packet(0).recent) == 1

@pytest.mark.parametrize('change', ['future', 'wrong_command', 'hypothetical_recent', 'reverse', 'stale_tail'])
def test_packet_constructor_closes_direct_construction_bypass(change):
    p = packet(2)
    with pytest.raises((ValueError, PermissionError)):
        if change == 'future':
            replace(p, recent=(replace(asset(2), available_at=3),))
        elif change == 'wrong_command':
            replace(p, command_id='other')
        elif change == 'hypothetical_recent':
            replace(p, recent=(asset(2, VisualRole.HYPOTHETICAL_OUTCOME),))
        elif change == 'reverse':
            replace(p, recent=(asset(2), asset(1)))
        else:
            replace(p, recent=(asset(1),))

def test_external_demonstration_needs_reference_role_and_grant():
    ref = asset(50, VisualRole.OUTCOME_REFERENCE, episode='training-demo')
    goal = VisualGoal('g', GoalKind.OUTCOME, 'e', 'open', 'drawer visibly open', (ref,))
    with pytest.raises(PermissionError):
        packet(2, goal)
    grant = ReferenceGrant(ref.sha256, 'training-demo', 'fixture', 'allowed-demo-use', 0.0)
    packet(2, replace(goal, reference_grants=(grant,)))
    bad = replace(goal, references=(replace(ref, role=VisualRole.OBSERVATION),), reference_grants=(grant,))
    with pytest.raises(PermissionError):
        packet(2, bad)

@pytest.mark.parametrize('kind', ['reference', 'anchor', 'old', 'wrong_packet'])
def test_monitor_cannot_cite_outcomes_as_current_evidence(kind):
    p = packet(4)
    v = verdict(p)
    if kind == 'reference':
        v = replace(v, cited_asset_ids=('imagined-success',))
    elif kind == 'anchor':
        v = replace(v, cited_asset_ids=(p.anchor.asset_id,))
    elif kind == 'old':
        v = replace(v, cited_asset_ids=(p.recent[0].asset_id,))
    else:
        v = replace(v, packet_fingerprint='other')
    with pytest.raises(PermissionError):
        v.require(p)

def test_shadow_complete_never_becomes_task_truth(journal):
    m = ProgressMonitor(journal=journal)
    for n in (1, 2, 3):
        p = packet(n)
        s = m.accept(p, verdict(p))
        assert s.event_type == 'completion_candidate' and s.semantic_authority == 'advisory_only'
    assert journal.records('situated_monitor')[-1]['promoted'] is False

@pytest.mark.parametrize('confirmed,revision,expected', [(True, 'test', 'subgoal_complete'), (False, 'test', 'completion_candidate'), (True, 'wrong', 'completion_candidate')])
def test_promotion_is_independent_and_bound_to_qualified_model(journal, confirmed, revision, expected):
    m = ProgressMonitor(journal=journal, qualified_revision='test', independently_confirm=lambda *a: confirmed)
    p = packet(1)
    assert m.accept(p, verdict(p, revision=revision)).event_type == 'completion_candidate'
    p = packet(2)
    assert m.accept(p, verdict(p, revision=revision)).event_type == expected

def test_duplicate_and_reopened_monitor_cannot_double_count(journal):
    m = ProgressMonitor(journal=journal)
    p = packet(1)
    m.accept(p, verdict(p))
    for obj in (m, ProgressMonitor(journal=journal)):
        with pytest.raises(PermissionError):
            obj.accept(p, verdict(p))

def test_unknown_resets_completion_streak(journal):
    m = ProgressMonitor(journal=journal, qualified_revision='test', independently_confirm=lambda *a: True)
    m.accept(packet(1), verdict(packet(1)))
    m.accept(packet(2), verdict(packet(2), 'unknown'))
    assert m.accept(packet(3), verdict(packet(3))).event_type == 'completion_candidate'

def test_monitor_json_refuses_safety_and_extra_fields():
    p = packet(1)
    with pytest.raises(ValueError):
        parse_monitor_reply({'packet_fingerprint': p.fingerprint, 'status': 'complete', 'cited_asset_ids': ['img-1'], 'collision_clear': True}, p, source='x', revision='1')
