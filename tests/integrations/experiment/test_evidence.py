from __future__ import annotations

from dataclasses import replace

import pytest

from physical_harness.core.contracts import VerificationRequest
from physical_harness.integrations.experiment.curation import validated_coverage
from physical_harness.integrations.experiment.native import CoverageScan, ObjectBox
from physical_harness.integrations.experiment.snapshots import ExperimentContext
from physical_harness.integrations.experiment.validation import loads
from tests.integrations.experiment.test_runner import build


def test_actual_crop_pixels_parent_and_original_time(tmp_path):
    from io import BytesIO

    from PIL import Image
    runner, _, _, journal = build(tmp_path)
    try:
        runner.capture()
        cards = runner.memory.cards(runner.memory.cutoff(0))
        card = next(c for c in cards if c.kind == 'entity_view')
        crop = runner.memory.asset(card.asset_ids[0])
        parent = runner.memory.asset(crop.parent_id)
        assert crop.observed_end == parent.observed_end == 0
        assert parent.asset_id in card.asset_ids
        with Image.open(BytesIO(runner.memory.read_asset(crop.asset_id, runner.memory.cutoff(0)))) as image:
            assert image.size == (33, 33) and image.getpixel((16, 16)) == (230, 10, 10)
    finally:
        runner.close()
        journal.close()


def test_crop_outside_source_and_unqualified_coverage_rejected():
    with pytest.raises(ValueError):
        ObjectBox('ball', 'head', (10, 10, 9, 20), 'tennis ball')
    with pytest.raises(ValueError):
        CoverageScan('table', ('ball',), ('head',), .99, 'vlm_guess', 'not_seen')


def test_coverage_is_source_bound_and_does_not_move_object(tmp_path):
    runner, _, _, journal = build(tmp_path)
    try:
        runner.capture()
        scan = CoverageScan('table', ('ball',), ('head',), .92, 'depth_visibility', 'not_seen')
        observation = replace(runner.current, coverage=(scan,))
        notes = validated_coverage(observation, runner.current_ids, runner.world)
        assert notes[0].coverage == 'high' and notes[0].result == 'not_seen'
        assert runner.world.belief('ball', 'location') is None
        wrong = dict(runner.current_ids, head='missing')
        with pytest.raises(ValueError):
            validated_coverage(observation, wrong, runner.world)
    finally:
        runner.close()
        journal.close()


def test_stale_or_unbound_after_evidence_is_rejected(tmp_path):
    runner, _, _, journal = build(tmp_path)
    try:
        runner.capture()
        eid = next(iter(runner.current_ids.values()))
        request = VerificationRequest('q', 's', ('CLOSED(cabinet)',), after_evidence_ids=(eid,))
        assert runner.resolver.validate_after(eid, request, 0, 0)
        assert not runner.resolver.validate_after(eid, request, 10, 0)
        assert not runner.resolver.validate_after(eid, request, 1, .5)
        assert not runner.resolver.validate_after('missing', request, 0, 0)
    finally:
        runner.close()
        journal.close()


def test_roster_recent_visibility_does_not_freshen_old_location(tmp_path):
    runner, _, _, journal = build(tmp_path)
    try:
        runner.capture()
        old = next(iter(runner.current_ids.values()))
        runner.world.update('ball', 'location', '{"place":"kitchen"}', old)
        runner.world.add_evidence('later', 10, 'perception', runner.world._evidence(old)['uri'],
                                  loads(runner.world._evidence(old)['payload']))
        runner.world.update('ball', 'visibility', 'not_observed', 'later', epistemic='inferred')
        result = ExperimentContext(runner.world).build(now=10, goal='find ball',
                        focus_entities=('ball',), image_evidence=[])
        fields = result['field_provenance']['ball']
        assert fields['location']['age_s'] == 10 and fields['visibility']['age_s'] == 0
    finally:
        runner.close()
        journal.close()


def test_conflicting_same_time_belief_is_visible(tmp_path):
    runner, _, _, journal = build(tmp_path)
    try:
        runner.capture()
        eid = next(iter(runner.current_ids.values()))
        runner.world.update('ball', 'ON', 'table', eid)
        runner.world.update('ball', 'ON', 'floor', eid)
        result = ExperimentContext(runner.world).build(now=0, goal='find ball',
                        focus_entities=('ball',), image_evidence=[])
        conflict = result['unresolved_belief_conflicts'][0]
        assert (conflict['old'], conflict['new']) == ('table', 'floor')
    finally:
        runner.close()
        journal.close()
