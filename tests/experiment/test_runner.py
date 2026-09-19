from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from physical_harness.context_rich import RichContextPolicy
from physical_harness.experiment.actors import Goal
from physical_harness.experiment.fixture import FixtureNative, FixtureTransport, run_demo
from physical_harness.experiment.journal import Journal
from physical_harness.experiment.models import JsonModel, ModelSettings, Rates
from physical_harness.experiment.native import ObjectBox
from physical_harness.experiment.replay import export_replay, saved_decisions
from physical_harness.experiment.runner import Action, EpisodeRunner, RunLimits
from physical_harness.experiment.validation import loads


def build(tmp_path, *, native=None, transport=None, motion=True, observable=True,
          qualified=True, narrator=False, policy=None):
    episode = 'ep'
    native = native or FixtureNative(episode)
    journal = Journal(tmp_path / 'journal.sqlite', episode, max_microusd=0, max_calls=20)
    transport = transport or FixtureTransport()
    model = JsonModel(ModelSettings('fixture', paid=False), transport, journal,
                      {'default': Rates('0', '0', '0', 'synthetic')})
    runner = EpisodeRunner(
        tmp_path, episode, 'Close cabinet', native.bindings(),
        [Goal('closed', 'CLOSED(cabinet)', ('cabinet', 'open_state', 'closed'),
              'Green fixture pixels means closed', ('cabinet',),
              observable_from_rgb=observable,
              verifier_qualification='fixture-only' if qualified else None)],
        [Action('close-cabinet', 'Close cabinet', ('cabinet',), 'closed')],
        model, model, journal,
        limits=RunLimits(allow_motion=motion, max_decisions=4),
        context_policy=policy, narrator_model=model if narrator else None)
    return runner, native, transport, journal


def test_full_real_core_loop_and_frozen_replay(tmp_path):
    run = tmp_path / 'run'
    report = run_demo(run)
    assert report['harness_finished'] and report['http_requests'] == 0
    assert report['executive_calls'] == 2 and report['motion_calls'] == 1
    assert report['benchmark_success'] == 'not_claimed'
    decisions = saved_decisions(run)
    assert decisions[0]['base_context']['task_ledger'][0]['status'] == 'planned'
    assert decisions[-1]['base_context']['task_ledger'][0]['status'] == 'observed_complete'
    memory_path = run / 'episodic.sqlite'
    memory_hash = hashlib.sha256(memory_path.read_bytes()).digest()
    exported = export_replay(run, tmp_path / 'exports')
    assert hashlib.sha256(memory_path.read_bytes()).digest() == memory_hash
    first = loads((tmp_path / 'exports' / exported['files'][0]).read_bytes())
    last = loads((tmp_path / 'exports' / exported['files'][-1]).read_bytes())
    assert first['contexts']['M0'] == decisions[0]['base_context']
    assert first['contexts']['M1']['episodic_memory']['images'] == []
    assert first['contexts']['M2']['episodic_memory']['images']
    assert first['contexts']['M1']['episodic_memory']['cards'] == first['contexts']['M2']['episodic_memory']['cards']
    assert all(card['observed_end'] == 0 for card in first['contexts']['M2']['episodic_memory']['cards'])
    assert any(card['observed_end'] == 1 for card in last['contexts']['M2']['episodic_memory']['cards'])


def test_motion_requires_opt_in_and_still_stops(tmp_path):
    runner, native, transport, journal = build(tmp_path, motion=False)
    try:
        report = runner.run()
        assert report['error'] == 'PermissionError'
        assert native.t == 0 and native.stops == 1
        assert not report['harness_finished']
    finally:
        runner.close()
        journal.close()


@pytest.mark.parametrize('corruption', ['wrong_id', 'wrong_time', 'wrong_episode', 'no_stop'])
def test_bad_receipt_cannot_reach_verifier_or_complete_task(tmp_path, corruption):
    class Bad(FixtureNative):
        def run_skill(self, request):
            result = super().run_skill(request)
            if corruption == 'wrong_id':
                return replace(result, skill_id='other')
            if corruption == 'wrong_time':
                return replace(result, sim_time_end=float('nan'))
            if corruption == 'wrong_episode':
                return replace(result, metadata=dict(result.metadata, episode_id='other'))
            return replace(result, metadata=dict(result.metadata, stop_acknowledged=False))
    runner, native, transport, journal = build(tmp_path, native=Bad('ep'))
    try:
        report = runner.run()
        assert report['error'] is not None and not report['harness_finished']
        assert 'closed' in report['pending_goals']
        assert {r['role'] for r in report['accounting']['roles']} == {'executive'}
        assert native.stops == 1
    finally:
        runner.close()
        journal.close()


def test_unobservable_goal_does_not_trigger_futile_verifier_calls(tmp_path):
    runner, native, transport, journal = build(tmp_path, observable=False)
    try:
        report = runner.run()
        assert not report['harness_finished'] and report['pending_goals'] == ['closed']
        assert {r['role'] for r in report['accounting']['roles']} == {'executive'}
        assert report['motion_calls'] <= 2
    finally:
        runner.close()
        journal.close()


def test_unqualified_semantic_verdict_stays_diagnostic(tmp_path):
    runner, native, transport, journal = build(tmp_path, qualified=False)
    try:
        report = runner.run()
        assert not report['harness_finished'] and report['pending_goals'] == ['closed']
    finally:
        runner.close()
        journal.close()


def test_identity_candidates_block_task_verification(tmp_path):
    class Ambiguous(FixtureNative):
        def observe(self):
            value = super().observe()
            return replace(value, boxes=(ObjectBox('cabinet', 'head', (16, 8, 49, 41),
                                                  'cabinet', ('cabinet', 'other')),))
    runner, native, transport, journal = build(tmp_path, native=Ambiguous('ep'))
    try:
        report = runner.run()
        assert not report['harness_finished']
        assert report['pending_goals'] == ['closed']
        cards = runner.memory.cards(runner.memory.cutoff(runner.now()))
        card = next(c for c in cards if c.kind == 'entity_view')
        assert set(card.entity_ids) == {'cabinet', 'other'}
    finally:
        runner.close()
        journal.close()


def test_shadow_failure_does_not_change_action_or_base_context(tmp_path):
    runner, native, transport, journal = build(
        tmp_path, policy=RichContextPolicy(memory_metadata_bytes=1))
    try:
        report = runner.run()
        assert report['harness_finished'] and report['motion_calls'] == 1
        assert not report['memory_shadow_ok']
        for row in saved_decisions(tmp_path):
            assert 'episodic_memory' not in row['base_context']
    finally:
        runner.close()
        journal.close()


def test_shadow_bind_failure_does_not_block_motion_or_enter_context(tmp_path, monkeypatch):
    runner, native, transport, journal = build(tmp_path)

    def fail_bind(*args, **kwargs):
        raise RuntimeError('shadow bind unavailable')

    monkeypatch.setattr(runner.sidecar, 'bind_skill', fail_bind)
    try:
        report = runner.run()
        assert report['harness_finished'] and report['motion_calls'] == 1
        assert not report['memory_shadow_ok']
        for row in saved_decisions(tmp_path):
            assert 'episodic_memory' not in row['base_context']
    finally:
        runner.close()
        journal.close()


def test_background_narration_has_no_completion_authority(tmp_path):
    runner, native, transport, journal = build(tmp_path, narrator=True)
    try:
        report = runner.run()
        assert report['harness_finished'] and report['narrator_stopped']
        assert runner.ledger.get('closed').evidence
        assert all(not eid.startswith('caption') for eid in runner.ledger.get('closed').evidence)
    finally:
        runner.close()
        journal.close()


def test_changed_observation_after_reasoning_prevents_native_action(tmp_path):
    native = FixtureNative('ep')
    class AdvanceAfterDecision(FixtureTransport):
        def post(self, path, payload):
            response = super().post(path, payload)
            if path == '/responses' and 'tool' in payload['text']['format']['schema']['properties']:
                native.t += .5
            return response
    runner, native, transport, journal = build(tmp_path, native=native,
                                              transport=AdvanceAfterDecision())
    try:
        report = runner.run()
        assert not report['harness_finished'] and report['motion_calls'] == 0
        assert report['error'] == 'RuntimeError'
    finally:
        runner.close()
        journal.close()
