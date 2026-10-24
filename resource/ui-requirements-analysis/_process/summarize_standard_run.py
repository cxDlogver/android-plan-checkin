import json
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
run = work.parent
sys.path.insert(0, str(run.parent.parent / '.codex/skills/requirements-analysis/scripts'))
from model_tools import model_digest
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
model = read(work / 'analysis-model.json')
gate = read(run / 'gate-result.json')
review = read(work / 'model-review.json')
assert model['schemaVersion'] == 2
assert gate['semantic_digest'] == model_digest(model) == review['semantic_digest']
assert gate['gate_status'] == 'failed'
assert not model['questions']
assert len(model['states']) == 23 and not model['transitions'] and not model['requirements']
summary = {'schemaVersion': model['schemaVersion'], 'gateStatus': gate['gate_status'], 'semanticDigest': model_digest(model),
           'states': len(model['states']), 'localVisualTargets': sum(len(s['regions']) for s in read(work / 'evidence/visual-observations.json')['scenarios']),
           'sources': len(model['sources']), 'openProductQuestions': 0,
           'checks': {key: value['status'] for key, value in gate['checks'].items()},
           'modelFailures': [f['actual'] for f in gate['failures'] if f['rule_id'] == 'MODEL-001'],
           'independentReview': {'inputComplete': review['input_complete'], 'htmlRuntimeVerified': review['html_runtime_verified'], 'bundleDigest': review['bundle_digest']},
           'missingRequiredOutputs': [name for name in ['state-graph.json', 'atomic-requirements.json', 'requirement-graph.json', 'analysis-model.json', 'review-log.json', 'review.html', 'manifest.json'] if not (run / name).exists()]}
(work / 'evidence/standard-run-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=True))
