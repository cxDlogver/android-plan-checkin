import json
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
run = work.parent
repo = run.parent.parent
sys.path.insert(0, str(repo / '.codex/skills/requirements-analysis/scripts'))
import workflow
from model_tools import DIMENSIONS, model_digest, validate

read = lambda path: json.loads(path.read_text(encoding='utf-8'))
write = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
inventory = read(work / 'evidence/visual-observations.json')
model = read(work / 'analysis-model.json')
assert model['schemaVersion'] == 2
model['phase'] = 'incomplete'
shared = []
for c in inventory['sharedConstraints']:
    shared.append(c['title'] + '\uff1a' + '\uff1b'.join(c['checks']) + '\uff08\u6765\u6e90\uff1a' + c['source'] + '\uff09')
acceptance = [a['id'] + ' ' + a['title'] + '\uff1a' + a['interpretation'] for a in inventory['acceptance']]
model['features'] = [{'id': 'F-UI', 'title': 'UI-001\uff1aUI\u89c6\u89c9\u7a3f\u6837\u5f0f\u5bf9\u9f50',
                      'scope': 'PRD\u552f\u4e00\u9700\u6c42UI-001\uff1b\u4e0d\u589e\u52a0\u72ec\u7acb\u4e1a\u52a1\u529f\u80fd\u3002\u4ee5\u4e0b\u4e3a\u8be5\u9700\u6c42\u7684\u5171\u540c\u89c6\u89c9\u7ea6\u675f\u548c\u539f\u6587\u9a8c\u6536\u4e49\u52a1\uff0c\u4e0d\u4f2a\u88c5\u4e3a\u4ea7\u54c1\u8fc1\u79fb\u3002\n' + '\n'.join(shared + acceptance),
                      'entryStateIds': []}]
model['entryStateIds'] = []
model['transitions'] = []
model['requirements'] = []
model['questions'] = []
model['states'] = []
model['rounds'] = [{'id': 'BUILD-VISUAL-STATES', 'kind': 'build', 'nodeIds': [], 'checks': [],
                    'changes': [{'kind': 'add', 'entityId': 'F-UI', 'meaning': '\u627f\u8f7dUI-001\u53ca\u516c\u5171\u89c6\u89c9\u7ea6\u675f\uff1b\u4e0d\u628a\u9a8c\u6536\u68c0\u67e5\u70b9\u62c6\u4e3a\u65b0\u589e\u529f\u80fd\u3002', 'sourceIds': ['PRD', 'HUMAN-VISUAL-SCOPE']}], 'openFrontier': ['F-UI']}]
command_results = []

def attempt_save(label):
    write(work / 'analysis-model.json', model)
    try:
        result = workflow.save_current(run)
        command_results.append({'operation': 'workflow.save_current', 'unit': label, 'status': 'passed', 'result': result})
    except Exception as exc:
        command_results.append({'operation': 'workflow.save_current', 'unit': label, 'status': 'failed', 'error': str(exc)})
    write(work / 'evidence/incremental-save-results.json', command_results)

for scenario in inventory['scenarios']:
    refs = [{'sourceId': scenario['imageSourceId'], 'frameId': scenario['frameId'], 'region': '\u753b\u677f\u6574\u4f53\uff0c\u903b\u8f91\u5c3a\u5bf8' + str(scenario['canvasSize']['width']) + '\u00d7' + str(scenario['canvasSize']['height']), 'stateLabel': scenario['title']}]
    facts = ['\u89c6\u89c9\u7eb3\u5165\u8fb9\u754c\uff1a' + scenario['condition']] + scenario['facts']
    for region in scenario['regions']:
        refs.append({'sourceId': 'TREE', 'frameId': scenario['frameId'],
                     'region': region['name'] + '\uff1b\u8282\u70b9\uff1a' + '\u3001'.join(n['nodeId'] for n in region['nodeRefs']), 'stateLabel': region['name']})
        facts.append('\u5c40\u90e8\u89c6\u89c9\u7ea6\u675f\uff1a' + region['name'] + '\uff1a' + '\uff1b'.join(region['checks']))
    facts += ['\u6837\u4f8b\u53c2\u6570\uff1a' + '\u3001'.join(scenario['parameters']) + '\uff1b\u6309\u5bf9\u5e94\u89c6\u89c9\u76ee\u6807\u6838\u5bf9\uff0c\u4e0d\u6269\u4e3a\u5168\u90e8\u53d6\u503c\u7ec4\u5408\u3002',
              '\u540c\u5c42\u7ea7\u533a\u5206\uff1a' + scenario['distinction'], '\u5206\u6790\u8fb9\u754c\uff1a' + '\uff1b'.join(scenario['excluded'])]
    state = {'id': scenario['id'], 'featureIds': ['F-UI'], 'title': scenario['title'] + '\u89c6\u89c9\u72b6\u6001',
             'facts': facts, 'uiRefs': refs, 'sourceIds': ['PRD', scenario['imageSourceId'], 'TREE', 'TOKENS'], 'status': 'draft'}
    model['states'].append(state)
    model['rounds'][0]['nodeIds'].append(state['id'])
    model['rounds'][0]['changes'].append({'kind': 'add', 'entityId': state['id'], 'meaning': scenario['distinction'], 'sourceIds': state['sourceIds']})
    if scenario['order'] in [6, 12, 18, 23]:
        attempt_save('source-backed visual states 1-' + str(scenario['order']))

audit = {'id': 'AUDIT-CURRENT-VISUAL-STATES', 'kind': 'audit', 'modelDigest': model_digest(model),
         'nodeIds': [s['id'] for s in model['states']], 'checks': [], 'changes': [], 'openFrontier': ['F-UI']}
model['rounds'].append(audit)
for scenario in inventory['scenarios']:
    target = next(s for s in model['states'] if s['id'] == scenario['id'])
    checks = {
        'sources': ('covered', 'PRD\u7b2c3\u8282\u56fe' + str(scenario['order']).zfill(2) + '\u3001\u753b\u677f' + scenario['frameId'] + '\u53ca\u5df2\u4fdd\u5b58\u89c2\u5bdf\u9010\u9879\u5bf9\u5e94\uff1b' + scenario['distinction']),
        'events': ('not_applicable', '\u672c\u72b6\u6001\u53ea\u6838\u5bf9\u201c' + scenario['title'] + '\u201d\u753b\u51fa\u7684\u5916\u89c2\uff1bPRD\u7b2c1.1\u30011.2\u30015\u8282\u672a\u8981\u6c42\u636e\u53ef\u89c1\u63a7\u4ef6\u63a8\u5bfc\u64cd\u4f5c\u7ed3\u679c\u3002' + '\uff1b'.join(scenario['excluded'])),
        'guard_complement': ('not_applicable', '\u89c6\u89c9\u7eb3\u5165\u6761\u4ef6\u5df2\u5199facts\uff1b\u672c\u72b6\u6001\u6ca1\u6709\u8303\u56f4\u5185\u4ea7\u54c1\u8fc1\u79fb\u6216\u4e1a\u52a1\u5b88\u536b\uff0c\u4e0d\u80fd\u628a\u201c' + scenario['condition'] + '\u201d\u673a\u68b0\u7ffb\u8f6c\u6210\u65b0\u6d41\u7a0b\u3002'),
        'boundaries': ('covered', '\u4fdd\u7559\u5df2\u6709\u7ed3\u6784\u4e0e\u5c40\u90e8\u5dee\u5f02\uff1a' + scenario['distinction'] + ' \u53c2\u6570\u201c' + '\u3001'.join(scenario['parameters']) + '\u201d\u4e0d\u505a\u7b1b\u5361\u5c14\u79ef\u3002'),
        'failure': ('not_applicable', '\u201c' + scenario['title'] + '\u201d\u4e2d\u7684\u5df2\u753b\u7ed3\u679c\u6216\u63d0\u793a\u7531\u5c40\u90e8\u89c6\u89c9\u7ea6\u675f\u627f\u8f7d\uff1bPRD\u7b2c5\u8282\u660e\u786e\u4e0d\u8865\u52a0\u8f7d\u3001\u4fdd\u5b58\u4e2d\u3001\u5176\u4ed6\u5f02\u5e38\u6216\u5b9e\u73b0\u526f\u4f5c\u7528\uff0c\u4e0d\u6784\u9020\u5931\u8d25\u8fc1\u79fb\u3002'),
        'cancel_return': ('not_applicable', '\u672c\u753b\u677f\u4e2d\u5df2\u753b\u6309\u94ae\u7684\u6587\u5b57\u3001\u4e3b\u6b21\u5173\u7cfb\u548c\u5916\u89c2\u6309\u5bf9\u5e94\u533a\u57df\u6838\u5bf9\uff1b' + '\u3001'.join(r['name'] for r in scenario['regions']) + '\u4e0d\u8bc1\u660e\u53d6\u6d88\u3001\u8fd4\u56de\u6216\u6062\u590d\u540e\u7684\u4ea7\u54c1\u7ec8\u6001\u3002'),
        'repeat_time': ('not_applicable', '\u201c' + '\u3001'.join(scenario['parameters']) + '\u201d\u662f\u89c6\u89c9\u6837\u4f8b\u53c2\u6570\u3002PRD\u4e0d\u8ffd\u52a0\u8de8\u65e5\u6216\u4e1a\u52a1\u65f6\u95f4\u673a\u5236\uff0c\u4e0d\u7531\u6240\u793a\u65e5\u671f\u548c\u65f6\u95f4\u63a8\u51fa\u91cd\u590d\u64cd\u4f5c\u5206\u652f\u3002'),
        'permissions': ('not_applicable', '\u201c' + scenario['title'] + '\u201d\u91cc\u7684\u53ea\u8bfb\u3001\u8b66\u793a\u6216\u72b6\u6001\u6587\u5b57\u4ec5\u627f\u62c5\u5df2\u753b\u89c6\u89c9\u4e49\u52a1\uff1bPRD\u7b2c5\u8282\u6392\u9664\u6743\u9650\u5b9e\u73b0\uff0c\u4e0d\u589e\u52a0\u8eab\u4efd\u3001\u89d2\u8272\u6216\u53ef\u64cd\u4f5c\u8d44\u683c\u72b6\u6001\u3002'),
        'ui': ('covered', '\u9010\u9879\u627f\u8f7d' + str(len(scenario['regions'])) + '\u4e2a\u5df2\u6709\u533a\u57df\uff1a' + '\uff1b'.join(r['name'] + '\uff08' + '\u3001'.join(r['anchors']) + '\uff09' for r in scenario['regions']) + '\u3002\u5c40\u90e8\u6837\u4f8b\u4e0d\u63d0\u5347\u4e3a\u6574\u9875\uff1bPNG\u4e0e\u6811\u8282\u70b9\u5f15\u7528\u5747\u4fdd\u7559\u3002'),
        'cross_feature': ('covered', '\u552f\u4e00\u529f\u80fd\u5f52\u5c5eF-UI\uff1b\u5171\u7528\u89c6\u89c9\u53c2\u6570\u4e0d\u65b0\u589e\u529f\u80fd\u3002' + scenario['distinction'] + ' \u672a\u4f9d\u636e\u9875\u9762\u540d\u79f0\u8fde\u63a5\u4e1a\u52a1\u6d41\uff1b\u5408\u540c\u8981\u6c42\u4e1a\u52a1\u5165\u53e3\u4f46\u5f53\u524d\u8303\u56f4\u65e0\u6b64\u4e49\u52a1\uff0c\u5de5\u5177\u8868\u8fbe\u51b2\u7a81\u4fdd\u7559\u5728scope\u524d\u6cbf\u3002')}
    assert set(checks) == DIMENSIONS
    for dimension, (disposition, reason) in checks.items():
        audit['checks'].append({'nodeId': target['id'], 'dimension': dimension, 'disposition': disposition,
                                'reason': reason, 'evidenceIds': target['sourceIds'], 'relatedIds': [target['id'], 'F-UI']})
    attempt_save('audit ' + target['id'])

assert audit['modelDigest'] == model_digest(model)
errors, warnings = validate(model)
state = read(work / 'run-state.json')
state.update({'phase': 'incomplete', 'round_id': audit['id'], 'active_node_id': None,
              'semantic_digest': model_digest(model), 'pending_node_ids': workflow.pending_nodes(model),
              'open_question_ids': [], 'waiting_for_user': False,
              'pause_reason': 'Skill\u5408\u540c\u4e0d\u80fd\u8868\u8fbe\u5df2\u6709\u9759\u6001\u89c6\u89c9\u7ea6\u675f\uff1a\u7981\u6b62\u9020\u5165\u53e3\u548c\u8fc1\u79fb\uff0c\u540c\u65f6\u5f3a\u5236\u5165\u53e3\u3001\u8fc1\u79fb\u4e0e\u884c\u4e3a\u9700\u6c42\u975e\u7a7a\u3002\u9700\u6c42\u8303\u56f4\u5df2\u660e\u786e\uff0c\u4e0d\u662f\u7528\u6237\u672a\u7b54\u95ee\u9898\u3002',
              'next_action': 'Run standard prepare/assert and preserve actual failures. Do not invent business states or change the Skill to force a pass.'})
write(work / 'run-state.json', state)
write(work / 'evidence/standard-model-validation.json', {'status': 'failed' if errors else 'passed', 'errors': errors, 'warnings': warnings,
      'semanticDigest': model_digest(model), 'states': len(model['states']), 'transitions': len(model['transitions']), 'atomicRequirements': len(model['requirements']),
      'userRequirement': 'UI-001 remains the sourced visual obligation in scope, feature constraints and state facts; no behavioral atom is invented.'})
print(json.dumps({'states': len(model['states']), 'regions': sum(len(s['regions']) for s in inventory['scenarios']), 'auditChecks': len(audit['checks']),
                  'standardSaveAttempts': len(command_results), 'errors': errors, 'semanticDigest': model_digest(model)}, ensure_ascii=True))
