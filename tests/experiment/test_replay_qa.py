from __future__ import annotations

from physical_harness.evidence import EvidenceStore
from physical_harness.experiment.fixture import run_demo
from physical_harness.experiment.journal import Journal
from physical_harness.experiment.models import JsonModel, ModelSettings, Rates
from physical_harness.experiment.replay import evaluate_qa, export_replay
from physical_harness.experiment.validation import dumps, loads
from physical_harness.memory.spatial_views import PosedRGBDKeyframe, SpatialViewIndex
from physical_harness.memory.store import MemoryStore


def _pose(x):
    return (1.0, 0.0, 0.0, x, 0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def test_posed_replay_is_causal_and_excludes_current_image_duplicates(tmp_path):
    run = tmp_path / 'run'
    run_demo(run)
    blobs = EvidenceStore(run / 'evidence')
    memory = MemoryStore(run / 'episodic.sqlite', 'fixture-episode', blobs.read)
    try:
        assets = {}
        for card in memory.cards(memory.cutoff(1)):
            for asset_id in card.asset_ids:
                asset = memory.asset(asset_id)
                if asset.kind == 'image':
                    assets[asset.observed_end] = asset
        spatial = SpatialViewIndex('fixture-episode')
        for observed_at, asset in sorted(assets.items()):
            spatial.add_keyframe(PosedRGBDKeyframe(
                keyframe_id=f'posed-{observed_at}',
                episode_id='fixture-episode',
                observation_id=asset.observation_id,
                sim_time=observed_at,
                camera=asset.camera,
                rgb_asset_id=asset.asset_id,
                depth_ref=f'native-depth-{observed_at}',
                pose_frame='local_map',
                camera_to_frame=_pose(observed_at),
                pose_source='rgbd_odometry',
                pose_confidence=.9,
                pose_evidence_ids=(asset.observation_id,),
                reason='decision_required',
                entity_ids=('cabinet',),
                place_ids=('fixture-room',),
            ))
        (run / 'spatial-memory.json').write_bytes(dumps(spatial.snapshot()))
    finally:
        memory.close()

    exports = tmp_path / 'exports'
    export_replay(run, exports)
    first = loads((exports / 'decision-0000.json').read_bytes())
    last = loads((exports / 'decision-0001.json').read_bytes())
    assert first['contexts']['M2_spatial']['spatial_memory']['keyframes'] == []
    historical = last['contexts']['M2_spatial']['spatial_memory']['keyframes']
    assert len(historical) == 1 and historical[0]['sim_time'] == 0
    assert last['contexts']['M2_spatial']['episodic_memory']['images'] == []


def test_qa_uses_saved_context_and_never_sends_evaluation_labels(tmp_path):
    run = tmp_path / 'run'
    run_demo(run)
    exports = tmp_path / 'exports'
    export_replay(run, exports)
    labels = tmp_path / 'labels.json'
    labels.write_bytes(dumps([{'question_id':'q', 'decision_file':'decision-0000.json',
        'question':'Is the state observable?', 'expected_evidence_ids':[], 'must_abstain':True}]))
    contexts = []
    class QA:
        def post(self, path, payload):
            if path.endswith('input_tokens'):
                return {'input_tokens':100}
            context = loads(payload['input'][0]['content'][0]['text'])
            contexts.append(context)
            assert 'expected_evidence_ids' not in context and 'must_abstain' not in context
            cards = context.get('episodic_memory', {}).get('cards', [])
            citations = [cards[0]['card_id']] if cards else []
            return {'id':'qa', 'status':'completed', 'service_tier':'default',
                    'usage':{'input_tokens':100,'output_tokens':30},
                    'output':[{'type':'message','role':'assistant','content':[
                        {'type':'output_text','text':dumps({'answer':'unknown','uncertain':True,
                                                          'evidence_ids':citations}).decode()}]}]}
    journal = Journal(tmp_path / 'qa.sqlite', 'fixture-episode', max_microusd=0, max_calls=4)
    try:
        model = JsonModel(ModelSettings('test-only', paid=False), QA(), journal,
                          {'default': Rates('0','0','0','fixture')})
        result = evaluate_qa(export_dir=exports, labels_file=labels, model=model, journal=journal)
        assert len(result['answers']) == 4
        assert [r['variant'] for r in result['answers']] == ['M0','M1','M2','M2_spatial']
        assert all(r['semantic_correctness'] == 'requires_independent_review' for r in result['answers'])
        assert all(r['unknown_citation_ids'] == [] for r in result['answers'])
        assert 'episodic_memory' not in contexts[0]
        assert contexts[0]['task_ledger'][0]['status'] == 'planned'
    finally:
        journal.close()
