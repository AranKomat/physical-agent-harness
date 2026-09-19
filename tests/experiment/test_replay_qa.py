from __future__ import annotations

from physical_harness.experiment.fixture import run_demo
from physical_harness.experiment.journal import Journal
from physical_harness.experiment.models import JsonModel, ModelSettings, Rates
from physical_harness.experiment.replay import evaluate_qa, export_replay
from physical_harness.experiment.validation import dumps, loads


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
            return {'id':'qa', 'status':'completed', 'service_tier':'default',
                    'usage':{'input_tokens':100,'output_tokens':30},
                    'output':[{'type':'message','role':'assistant','content':[
                        {'type':'output_text','text':'{"answer":"unknown","uncertain":true,"evidence_ids":[]}'}]}]}
    journal = Journal(tmp_path / 'qa.sqlite', 'fixture-episode', max_microusd=0, max_calls=4)
    try:
        model = JsonModel(ModelSettings('test-only', paid=False), QA(), journal,
                          {'default': Rates('0','0','0','fixture')})
        result = evaluate_qa(export_dir=exports, labels_file=labels, model=model, journal=journal)
        assert len(result['answers']) == 3
        assert [r['variant'] for r in result['answers']] == ['M0','M1','M2']
        assert all(r['semantic_correctness'] == 'requires_independent_review' for r in result['answers'])
        assert 'episodic_memory' not in contexts[0]
        assert contexts[0]['task_ledger'][0]['status'] == 'planned'
    finally:
        journal.close()
