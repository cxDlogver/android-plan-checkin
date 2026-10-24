import hashlib
import json
from pathlib import Path

work = Path(__file__).resolve().parent
root = work.parent
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
manifest = read(root / 'manifest.json')
model = read(root / 'analysis.json')
missing = [name for name in ['state-graph.json', 'atomic-requirements.json', 'requirement-graph.json', 'analysis-model.json', 'review-log.json', 'gate-result.json'] if not (root / name).is_file()]
assert missing
assert model['phase'] == manifest['status'] == 'incomplete'
assert model['review']['independent'] == 'stale_after_contract_correction'
assert model['questions'] and model['questions'][0]['status'] == 'out_of_scope'
assert not any(q['status'] == 'open' for q in model['questions'])
assert model['clarityAssessment']['status'] == 'clear_for_visual_alignment'
assert read(work / 'run-state.json')['waitingForUser'] is False
for name, expected in manifest['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
assert '\u5b8c\u6574\u4e1a\u52a1\u8fc1\u79fb\u53cc\u56fe\u6d41\u7a0b\u4e0d\u9002\u7528' not in (root / 'analysis.md').read_text(encoding='utf-8')
html = (root / 'review.html').read_text(encoding='utf-8')
assert '\u9700\u6c42\u5206\u6790\u672a\u5b8c\u6210' in html and '\u53cc\u56fe\u5c1a\u7f3a' in html
result = {'status': 'incomplete', 'artifactIntegrity': 'passed', 'semanticDigest': manifest['semanticDigest'], 'bundleDigest': manifest['bundleDigest'], 'missingRequiredOutputs': missing, 'reason': '\u7f3a\u5c11\u901a\u7528\u89c4\u8303\u53cc\u56fe\u3001\u539f\u5b50\u9700\u6c42\u53ca\u5b8c\u6574\u9a8c\u6536\uff1b\u4e0a\u6b21\u89c6\u89c9\u8d44\u6599\u590d\u6838\u4e0d\u8bc1\u660e\u9700\u6c42\u5206\u6790\u5b8c\u6210\u3002'}
(work / 'delivery-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
