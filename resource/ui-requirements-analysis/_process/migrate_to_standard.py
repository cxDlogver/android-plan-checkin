import hashlib
import json
import shutil
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
run = work.parent
repo = run.parent.parent
skill = repo / '.codex/skills/requirements-analysis'
sys.path.insert(0, str(skill / 'scripts'))
from model_tools import scope_digest

read = lambda path: json.loads(path.read_text(encoding='utf-8'))
write = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
old = read(work / 'analysis-model.json')
assert old.get('modelKind') == 'visual_source_inventory', 'Migration accepts the former inventory once only.'
inventory = {key: old[key] for key in ['sources', 'scenarios', 'sharedConstraints', 'acceptance', 'coverage', 'scopeText', 'clarityAssessment']}
write(work / 'evidence/visual-observations.json', inventory)

bootstrap = (work / '_standard-init').resolve()
assert bootstrap.parent == work.resolve() and bootstrap.name == '_standard-init'
for name in ['gate-contract.json', 'run-state.json', 'analysis-model.json']:
    shutil.copy2(bootstrap / '_process' / name, work / name)
for name in ['gate-contract.json', 'run-state.json', 'analysis-model.json']:
    (bootstrap / '_process' / name).unlink()
(bootstrap / '_process/evidence').rmdir()
(bootstrap / '_process').rmdir()
bootstrap.rmdir()

for source_name, target_name in [('analysis.md', 'visual-source-notes.md'), ('review.html', 'visual-material-review.html'), ('manifest.json', 'visual-material-manifest.json')]:
    source = run / source_name
    target = work / 'evidence' / target_name
    assert source.resolve().parent == run.resolve() and target.resolve().parent == (work / 'evidence').resolve()
    if source.exists():
        source.replace(target)
(run / 'analysis.json').unlink()

model = read(work / 'analysis-model.json')
model['scope'] = {'objective': 'UI-001\uff1a\u4f9d\u636e\u5f53\u524dUI\u89c6\u89c9\u7a3f\uff0c\u5bf9\u9f5023\u5f20\u753b\u677f\u53ca\u5df2\u6709\u5c40\u90e8\u72b6\u6001\u7684\u6837\u5f0f\uff1b\u4ec5\u8fdb\u884c\u9700\u6c42\u5206\u6790\u3002',
                  'included': old['scopeText']['included'] + ['\u4fdd\u7559PRD A01\u81f3A08\u7684\u89c6\u89c9\u9a8c\u6536\u4e49\u52a1\uff1b\u6309\u901a\u7528Skill\u751f\u6210\u5206\u6790\u4ea7\u7269\u5e76\u6267\u884c\u771f\u5b9e\u95e8\u7981\u3002'],
                  'excluded': old['scopeText']['excluded'],
                  'abstraction': '\u9875\u9762\u7ea7\u89c6\u89c9\u72b6\u6001\uff1b\u5c40\u90e8\u7ec4\u4ef6\u6837\u4f8b\u4f5c\u4e3a\u6240\u5c5e\u72b6\u6001\u7684\u89c6\u89c9\u7ea6\u675f\uff0c\u4efb\u52a1\u540d\u3001\u65e5\u671f\u3001\u6570\u91cf\u548c\u5907\u6ce8\u4f5c\u4e3a\u5c55\u793a\u53c2\u6570\u3002\u53ea\u5206\u6790\u89c6\u89c9\u5224\u5b9a\uff0c\u4e0d\u4ee5\u53ef\u89c1\u6309\u94ae\u63a8\u5bfc\u4e1a\u52a1\u4e8b\u4ef6\u3001\u4e1a\u52a1\u5165\u53e3\u3001\u8def\u7531\u6216\u5b9e\u73b0\u3002'}
model['sources'] = old['sources']
for source in model['sources']:
    source.setdefault('locator', '\uff1b'.join(source['readRanges']))
reply = work / 'evidence/skill-analysis-user-instruction.md'
reply.write_text('# \u7528\u6237\u8303\u56f4\u4e0e\u6267\u884c\u6307\u4ee4\n\n\u7528\u6237\u8303\u56f4\u6f84\u6e05\u539f\u6587\uff1a\n\n\u9700\u6c42 \u662f\u8fdb\u884c UI \u89c6\u89c9\u7a3f\u7684\u6837\u5f0f\u5bf9\u9f50\uff0c \u9700\u6c42\u662f\u5426\u660e\u786e\uff0c PRD\u662f\u5426\u6f84\u6e05\uff0c \u662f\u5426\u5b58\u5728\u6a21\u7cca\u9700\u6c42\uff0c \u4e0d\u8003\u8651\u9700\u6c42\u4ee5\u5916\u7684\u5b9e\u73b0\n\n\u7528\u6237\u672c\u8f6e\u6307\u4ee4\u539f\u6587\uff1a\n\n\u6839\u636eskill \u8fdb\u884c\u9700\u6c42\u5206\u6790\n\n\u5f15\u7528\uff1a\u672c\u5bf9\u8bdd\u7528\u6237\u7684\u771f\u5b9e\u8303\u56f4\u6f84\u6e05\u4e0e\u5f53\u524d\u4efb\u52a1\u6307\u4ee4\u3002\u4ec5\u4f5c\u4e3a\u521d\u59cb\u8303\u56f4\u786e\u8ba4\uff0c\u4e0d\u4f5c\u4e3a\u6700\u7ec8\u9a8c\u6536\u3002\n', encoding='utf-8')
model['sources'].append({'id': 'HUMAN-SKILL-ANALYSIS', 'kind': 'human', 'uri': 'conversation:current-skill-analysis-user-request',
                         'locator': '\u672c\u5bf9\u8bdd\u5df2\u660e\u786e\u89c6\u89c9\u8303\u56f4\u7684\u7b54\u590d\u53ca\u5f53\u524d\u6267\u884c\u6307\u4ee4', 'evidencePath': '_process/evidence/skill-analysis-user-instruction.md',
                         'sha256': hashlib.sha256(reply.read_bytes()).hexdigest(), 'readRanges': ['\u8303\u56f4\u6f84\u6e05\u539f\u6587\u4e0e\u672c\u8f6e\u6267\u884c\u6307\u4ee4\u5168\u6587']})
model['confirmations'] = [{'stage': 'scope', 'humanReference': '\u7528\u6237\u5df2\u660e\u786e\u4ec5UI\u89c6\u89c9\u7a3f\u6837\u5f0f\u5bf9\u9f50\uff0c\u4e0d\u8003\u8651\u9700\u6c42\u5916\u5b9e\u73b0\uff1b\u968f\u540e\u6307\u4ee4\u201c\u6839\u636eskill \u8fdb\u884c\u9700\u6c42\u5206\u6790\u201d',
                           'summary': '\u5df2\u786e\u8ba4\u672c\u8f6e\u89c6\u89c9\u5206\u6790\u8303\u56f4\uff1b\u4e0d\u8ffd\u52a0\u4e1a\u52a1\u6d41\u7a0b\u6216\u5b9e\u73b0\uff0c\u53cc\u56fe\u4ea4\u4ed8\u4ecd\u9075\u5faaSkill\uff0c\u6700\u7ec8\u4eba\u5de5\u9a8c\u6536\u5c1a\u672a\u53d1\u751f\u3002',
                           'scopeDigest': scope_digest(model), 'sourceId': 'HUMAN-SKILL-ANALYSIS'}]
write(work / 'analysis-model.json', model)
state = read(work / 'run-state.json')
state['waiting_for_user'] = False
state['next_action'] = 'Scope is confirmed. Import source-backed visual states; do not ask for excluded business behavior.'
write(work / 'run-state.json', state)
print(json.dumps({'schemaVersion': model['schemaVersion'], 'sources': len(model['sources']), 'scopeConfirmed': True, 'workModel': str(work / 'analysis-model.json')}, ensure_ascii=True))
