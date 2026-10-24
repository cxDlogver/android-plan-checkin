import hashlib
import json
from pathlib import Path

work = Path(__file__).resolve().parent
root = work.parent
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda value: hashlib.sha256(value).hexdigest()
model = read(root / 'analysis.json')
manifest = read(root / 'manifest.json')
browser = read(work / 'evidence/browser-observation.json')
semantic = {key: value for key, value in model.items() if key not in model['digestExclusions']}
assert sha(json.dumps(semantic, sort_keys=True, ensure_ascii=False).encode('utf-8')) == model['semanticDigest'] == manifest['semanticDigest']
for name, expected in manifest['files'].items():
    assert sha((root / name).read_bytes()) == expected, name
assert sha(json.dumps(manifest['files'], sort_keys=True).encode('utf-8')) == manifest['bundleDigest']
assert browser['bundleDigest'] == manifest['bundleDigest']
assert browser['htmlSha256'] == manifest['files']['review.html']
assert len(browser['frames']) == len(model['scenarios']) == 23
assert all(frame['imageReady'] and not frame['horizontalOverflow'] for frame in browser['frames'])
assert sum(frame['regions'] for frame in browser['frames']) == sum(len(frame['regions']) for frame in model['scenarios']) == 50
assert browser['coverage']['sourceItems'] == len(model['coverage']) == 102
assert browser['coverage']['acceptanceItems'] == len(model['acceptance']) == 8
assert not browser['errorLogs']
assert 'fontSize' not in browser['renderedParameters']
assert 'fill_container' not in browser['renderedParameters']
assert 'regions' not in browser['coverage']['acceptanceTable']
assert model['review']['humanAcceptance'] == manifest['humanAcceptance'] == 'pending'
assert model['convergence']['productVisualAcceptance'] == 'not_run'
assert manifest['fixedSkillPipeline'] == 'not_run'
peer_path = work / 'model-review.json'
assert peer_path.is_file(), 'Independent final report is required before delivery.'
peer_text = peer_path.read_text(encoding='utf-8')
assert manifest['semanticDigest'] in peer_text and manifest['bundleDigest'] in peer_text
peer = json.loads(peer_text)
assert peer['status'] == 'completed_with_documented_limitations'
assert peer['semantic_digest'] == manifest['semanticDigest']
assert peer['bundle_digest'] == manifest['bundleDigest']
assert not peer['open_findings']
assert all(finding['status'] == 'resolved' for finding in peer['findings'])
for evidence in peer['evidence_files']:
    assert sha((root / evidence['path']).read_bytes()) == evidence['sha256'], evidence['path']
result = {'status': 'passed', 'kind': 'draft_artifact_integrity',
          'semanticDigest': manifest['semanticDigest'], 'bundleDigest': manifest['bundleDigest'],
          'frames': 23, 'regions': 50, 'sourceItems': 102, 'originalAcceptanceItems': 8,
          'scope': 'Exported-source visual analysis draft; not product visual acceptance or the full behavioral Skill gate pipeline.'}
(work / 'delivery-verification.json').write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
