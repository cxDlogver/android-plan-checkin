from pathlib import Path
import base64
import copy
import hashlib
import json
import re

WORK = Path(__file__).parent
RUN = WORK.parent
ROOT = RUN.parents[1]


def read(name):
    return json.loads((WORK / name).read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


model = read('analysis-model.json')
shared = read('shared-analysis.json')
design = read('design-index.json')
tokens = json.loads((WORK / 'evidence/design-tokens.json').read_text(encoding='utf-8'))
model.update(shared)
model['phase'] = 'incomplete'
model['scope']['objective'] = shared['requirement']['statement']
model['scope']['abstraction'] = shared['scopeText']['abstraction']
model['scope']['included'] = shared['scopeText']['included']
model['scope']['excluded'] = shared['scopeText']['excluded']

coverage = []
section = ''
source_text = (WORK / 'evidence/prd.md').read_text(encoding='utf-8')
for number, raw in enumerate(source_text.splitlines(), 1):
    line = raw.strip()
    heading = re.match(r'^#{2,3}\s+(\d+(?:\.\d+)*)', line)
    if heading:
        section = heading[1]
        continue
    if not section or section.startswith('7') or not line or line.startswith('#'):
        continue
    if line.startswith('|') and (
        re.match(r'^\|\s*[-:]+', line) or line.startswith('| \u7f16\u53f7') or line.startswith('| \u56fe |')
        or line.startswith('| \u7528\u9014') or line.startswith('| \u9879\u76ee') or line.startswith('| \u68c0\u67e5\u70b9')
    ):
        continue
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line).replace('**', '')
    targets = []
    disposition = '\u5df2\u6620\u5c04'
    if section == '1':
        targets = ['UI-001']
    elif section == '1.1':
        targets = ['\u5168\u90e8\u753b\u677f\u4e0e\u533a\u57df\u68c0\u67e5\u70b9', 'C06']
    elif section == '1.2':
        targets = ['\u8303\u56f4\u8fb9\u754c', 'C08']
        disposition = '\u6309\u539f\u6587\u9650\u5b9a\u8303\u56f4'
    elif section == '2':
        if line.startswith('| D1'):
            disposition = '\u539f\u7a3f\u5b9e\u65f6\u6838\u5bf9\u53d7\u9650'
            targets = ['\u9650\u5236L1\uff1b\u73b0\u6709\u5bfc\u51fa\u56fe\u4e0e\u5feb\u7167']
        elif line.startswith('| D2'):
            targets = ['23\u4e2aPNG\u6765\u6e90\u4e0e\u9010\u9875\u89c2\u5bdf']
        elif line.startswith('| D3'):
            targets = ['\u4ec5\u4f7f\u7528\u6620\u5c04\u7684\u753b\u677f\u7f16\u53f7\uff0f\u540d\u79f0\uff0fID\uff0f\u5c3a\u5bf8\uff0f\u56fe\u7247\u8def\u5f84']
        elif line.startswith('| D4'):
            targets = ['C02\u2013C07\uff1b\u89c6\u89c9\u4ee4\u724c']
        elif line.startswith('| D5'):
            targets = ['\u5404\u533a\u57dfnodeRefs\uff1b\u5c40\u90e8\u8bbe\u8ba1\u53c2\u6570']
        elif re.match(r'^2\.', line):
            targets = ['C08']
        elif re.match(r'^3\.', line):
            targets = ['\u6765\u6e90\u51b2\u7a81\u5904\u7f6e', '\u9650\u5236L1']
        else:
            targets = ['\u6765\u6e90\u4f7f\u7528\u539f\u5219', 'C08']
    elif section == '3':
        match = re.match(r'^\|\s*(\d{2})\s*\|', line)
        if match:
            order = int(match[1])
            scenario = next(s for s in model['scenarios'] if s['order'] == order)
            targets = [f"\u56fe{order:02} {scenario['title']}", *[r['name'] for r in scenario['regions']]]
        elif '\u56fe16' in line:
            targets = ['\u56fe16\u4e09\u4e2a\u5c40\u90e8\u76ee\u6807', 'C08']
        else:
            targets = ['C01']
    elif section == '4':
        targets = ['C02\u2013C07\uff1b\u5c40\u90e8\u8282\u70b9\u4f18\u5148']
    elif section == '4.1':
        targets = ['C05', 'C06', 'C04']
    elif section == '4.2':
        targets = ['C05'] if '\u6e10\u53d8' in line else ['C02']
    elif section == '4.3':
        if '\u56fe\u6807' in line:
            targets = ['C06']
        elif any(t in line for t in ['\u5b57\u4f53', '\u5b57\u53f7', '\u5b57\u91cd', '\u884c\u9ad8', 'sp', '\u9875\u9762\u6807\u9898', '\u6b63\u6587', '\u91cd\u8981\u6807\u7b7e', '\u533a\u5757\u6807\u9898']):
            targets = ['C03']
        else:
            targets = ['C04']
    elif section == '4.4':
        targets = ['\u56fe11\u6708\u5386\u4e0e\u65e5\u671f\u683c\u6837\u4f8b', '\u56fe11\u7b5b\u9009\u4e0e\u5f69\u8272\u660e\u7ec6', 'C07']
    elif section == '5':
        targets = ['\u8303\u56f4\u5916\u6e05\u5355', 'C08']
        disposition = '\u6309\u539f\u6587\u6392\u9664\u6269\u5c55'
    elif section == '6':
        match = re.match(r'^\|\s*(A\d{2})', line)
        targets = [match[1], '\u5bf9\u5e94\u9a8c\u6536\u6620\u5c04'] if match else ['UI-001\uff1b\u9a8c\u6536\u542b\u4e49']
    elif section == '6.1':
        targets = ['C09', 'C08']
    else:
        raise ValueError(f'Unmapped source section {section}: {line}')
    coverage.append({'id': f'PRD-L{number}', 'sourceId': 'PRD', 'line': number,
                     'section': '\u00a7' + section, 'text': text.strip('| '),
                     'targets': targets, 'disposition': disposition})

model['coverage'] = coverage
for source in model['sources']:
    source['kind'] = 'prd' if source['id'] == 'PRD' else 'ui'
    if source['id'] == 'TREE':
        source['readRanges'] = ['mapped 23 frame subtrees and reusable visual children; node paths and parameters extracted',
                                'all named scenario regions cross-checked with viewed PNGs']

errors = []
mapped_screens = design['screens']
if len(model['scenarios']) != len(mapped_screens):
    errors.append('Scenario count differs from source map')
if {s['frameId'] for s in model['scenarios']} != {s['frameId'] for s in mapped_screens}:
    errors.append('Frame coverage mismatch')
for source in model['sources']:
    path = RUN / source['evidencePath']
    if not path.exists() or sha(path.read_bytes()) != source['sha256']:
        errors.append('Source evidence mismatch: ' + source['id'])
for s in model['scenarios']:
    if s['pngSize'] != [s['canvasSize']['width'] * 2, s['canvasSize']['height'] * 2]:
        errors.append('PNG scale mismatch: ' + s['id'])
    if s['treeSize'] != s['canvasSize']:
        errors.append('Tree size mismatch: ' + s['id'])
    for key in ['condition', 'facts', 'distinction', 'regions', 'parameters', 'excluded']:
        if not s.get(key):
            errors.append('Missing scenario definition: ' + s['id'] + '/' + key)
    nodes = next(x['nodes'] for x in mapped_screens if x['frameId'] == s['frameId'])
    for region in s['regions']:
        missing = [a for a in region['anchors']
                   if not any(n.get('name') == a or n.get('content') == a for n in nodes)]
        if missing:
            errors.append('Missing design anchors: ' + region['id'] + ': ' + ', '.join(missing))
        if not region['checks'] or not region['nodeRefs']:
            errors.append('Empty local checks or source nodes: ' + region['id'])
if {a['id'] for a in model['acceptance']} != {f'A{i:02}' for i in range(1, 9)}:
    errors.append('PRD acceptance coverage mismatch')
if len([r for r in coverage if r['section'] == '\u00a73' and any(t.startswith('\u56fe') for t in r['targets'])]) < 23:
    errors.append('PRD section 3 frame inventory missing')
if errors:
    write_json(WORK / 'validation-result.json', {'status': 'failed', 'errors': errors})
    raise ValueError('\n'.join(errors))

model['digestExclusions'] = ['convergence', 'phase', 'review', 'rounds', 'semanticDigest']
semantic = {k: v for k, v in model.items() if k not in model['digestExclusions']}
semantic_digest = sha(json.dumps(semantic, sort_keys=True, ensure_ascii=False).encode('utf-8'))
model['semanticDigest'] = semantic_digest
model['rounds'] = [
    {'kind': 'build', 'context': 'current_author_context',
     'evidence': ['observations-01.json', 'observations-02.json', 'observations-03.json', 'observations-04.json'],
     'meaning': 'Viewed all 23 PNGs in four batches, read matching design nodes and saved each batch.'},
    {'kind': 'author_audit', 'semanticDigest': semantic_digest,
     'checks': [{'scenarioId': s['id'], 'sourceBoundary': s['condition'],
                 'splitReason': s['distinction'], 'scopeBoundary': s['excluded'],
                 'regionCount': len(s['regions']), 'disposition': 'reviewed_against_png_tree_prd'}
                for s in model['scenarios']],
     'sourceCoverage': 'all scoped PRD items have a mapping or explicit boundary/limitation',
     'newUnsupportedStates': [], 'pendingFrameObservations': []}
]
model['convergence'] = {
    'scope': 'current accessible PRD and exported design materials',
    'frameObservationsComplete': True, 'sourceInventoryMapped': True,
    'originalNativeFileLiveVerified': False, 'authorAuditComplete': True,
    'independentReview': model.get('review', {}).get('independent', 'pending'),
    'humanFinalConfirmation': 'pending', 'productVisualAcceptance': 'not_run',
    'fullSkillPipeline': 'incomplete_required_outputs_missing'
}
write_json(WORK / 'analysis-model.json', model)
write_json(RUN / 'analysis.json', model)
write_json(WORK / 'validation-result.json', {
    'status': 'passed', 'semanticDigest': semantic_digest,
    'checks': ['all 23 source frames mapped', 'all PNG dimensions 2x', 'map/tree size agreement',
               'source evidence SHA256', 'scenario definition fields', 'local design anchor references',
               'A01-A08 presence', 'scoped PRD source disposition'],
    'limitations': 'Structure and references only; does not prove semantics, native design currency, human acceptance or app implementation.',
    'frameCount': len(model['scenarios']), 'regionCount': sum(len(s['regions']) for s in model['scenarios']),
    'coverageItemCount': len(coverage), 'errors': []})

def readable_target(value):
    for start in range(1, 10):
        for end in range(start, 10):
            titles = '\u3001'.join(c['title'] for c in model['sharedConstraints'] if start <= int(c['id'][1:]) <= end)
            for sep in ['\u2013', '\u2014', '-']:
                value = value.replace(f'C{start:02}{sep}C{end:02}', titles)
    for constraint in model['sharedConstraints']:
        value = value.replace(constraint['id'], constraint['title'])
    return value.replace('regions', '\u533a\u57df\u68c0\u67e5\u70b9').replace('facts', '\u754c\u9762\u4e8b\u5b9e')

coverage_md = ['# \u5f53\u524d\u6765\u6e90\u8986\u76d6\u8bb0\u5f55', '',
               '\u5df2\u6620\u5c04\u8868\u793a\u5206\u6790\u627f\u8f7d\uff0c\u4e0d\u8868\u793a\u4ea7\u54c1\u901a\u8fc7\u3002\u539f\u7a3f\u5b9e\u65f6\u4e00\u81f4\u6027\u53d7\u9650\uff0c\u89c1L1\u3002', '',
               '| \u539f\u6587\u4f4d\u7f6e | \u8981\u6c42\uff0f\u8fb9\u754c | \u5bf9\u5e94\u76ee\u6807 | \u5904\u7f6e |', '| --- | --- | --- | --- |']
for row in coverage:
    clean = lambda s: str(s).replace('|', '\uff0f').replace('\n', ' ')
    coverage_md.append('| ' + ' | '.join(map(clean, [
        row['section'] + ' \u00b7 L' + str(row['line']), row['text'], '\uff1b'.join(row['targets']), row['disposition']
    ])) + ' |')
(WORK / 'evidence/source-coverage.md').write_bytes(('\n'.join(coverage_md) + '\n').encode('utf-8'))

report = ['# \u5f53\u524d\u9700\u6c42\u5206\u6790\uff1aUI\u8bbe\u8ba1\u8fd8\u539f', '',
          '\u9636\u6bb5\uff1a\u672a\u5b8c\u6210\u901a\u7528\u9700\u6c42\u5206\u6790\u89c4\u8303\u3002\u73b0\u6709\u6587\u4ef6\u4ec5\u4e3a\u89c6\u89c9\u8d44\u6599\u6574\u7406\uff0c\u5c1a\u7f3a\u72b6\u6001\u8fc1\u79fb\u56fe\u3001\u9700\u6c42\u56fe\u3001\u539f\u5b50\u9700\u6c42\u53ca\u5b8c\u6574\u9a8c\u6536\uff1b\u64a4\u56de\u6b64\u524d\u6574\u4f53\u5b8c\u6210\u7ed3\u8bba\u3002', '',
          '## \u7ed3\u8bba\u4e0e\u8303\u56f4', '',
          model['requirement']['statement'], '', model['requirement']['countingRule'], '',
          '\u672c\u6b21\u9010\u4e00\u67e5\u770b23\u5f20PNG\uff0c\u5e76\u4e0e\u9875\u9762\u6620\u5c04\u3001\u8bbe\u8ba1\u6811\u5feb\u7167\u548c\u89c6\u89c9\u4ee4\u724c\u4ea4\u53c9\u6838\u5bf9\u3002\u72b6\u6001\u8fc1\u79fb\u56fe\u548c\u9700\u6c42\u56fe\u4ecd\u4e3a\u5fc5\u9700\u4ea4\u4ed8\uff1b\u4e0d\u5f97\u56e0\u4ec5\u89c6\u89c9\u8303\u56f4\u7701\u7565\uff0c\u4e5f\u4e0d\u5f97\u865a\u6784\u5165\u53e3\u3001\u4e8b\u4ef6\u6216\u7531\u6837\u5f0f\u62c6\u51fa\u4e1a\u52a1\u529f\u80fd\u3002\u5f53\u524d\u5165\u53e3\u4e0e\u8fc1\u79fb\u4f9d\u636e\u5f85\u6f84\u6e05\u3002', '',
          '\u5df2\u5f62\u621023\u4e2a\u753b\u677f\u7ea7\u89c6\u89c9\u5bf9\u7167\u573a\u666f\u548c' + str(sum(len(s['regions']) for s in model['scenarios'])) + '\u4e2a\u533a\u57df\u68c0\u67e5\u70b9\u3002\u8be5\u6570\u91cf\u6765\u81ea\u672c\u6b21\u8d44\u6599\u7684\u533a\u5206\u4e0e\u8986\u76d6\uff0c\u4e0d\u662f\u901a\u7528\u72b6\u6001\u6570\u91cf\u89c4\u5219\u3002', '',
          '## \u7eb3\u5165\u4e0e\u6392\u9664', '']
report += ['- ' + x for x in model['scopeText']['included']]
report += ['', '\u8303\u56f4\u5916\uff1a', ''] + ['- ' + x for x in model['scopeText']['excluded']]
report += ['', '## \u753b\u677f\u7ea7\u573a\u666f\u4e0e\u72b6\u6001\u8fb9\u754c', '',
           '| \u56fe | \u573a\u666f | \u903b\u8f91\u5c3a\u5bf8 | \u72ec\u7acb\u89c6\u89c9\u4e49\u52a1 |', '| --- | --- | --- | --- |']
for s in model['scenarios']:
    report.append(f"| {s['order']:02} | {s['title']} | {s['canvasSize']['width']}\u00d7{s['canvasSize']['height']} | {s['distinction']} |")
report += ['', '## \u9010\u9875\u89c6\u89c9\u8981\u6c42', '']
for s in model['scenarios']:
    report += [f"### \u56fe{s['order']:02} {s['title']}", '',
               f"\u6765\u6e90\uff1aPRD\u7b2c3\u8282\u56fe{s['order']:02}\uff1b\u753b\u677f{s['frameId']}\uff1b\u5bf9\u5e94PNG\uff1b\u8bbe\u8ba1\u6811\u540c\u540d\u753b\u677f\u53ca\u8282\u70b9\u3002", '',
               '\u7eb3\u5165\u6761\u4ef6\uff1a' + s['condition'], '', '\u5f53\u524d\u4e8b\u5b9e\uff1a', '']
    report += ['- ' + f for f in s['facts']]
    report += ['', '\u5c40\u90e8\u5bf9\u9f50\u68c0\u67e5\uff1a', '']
    for region in s['regions']:
        report.append('- ' + region['name'] + '\uff1a' + '\uff1b'.join(region['checks']))
    report += ['', '\u5c55\u793a\u53c2\u6570\uff1a' + '\u3001'.join(s['parameters']) + '\u3002', '',
               '\u672c\u8f6e\u8fb9\u754c\uff1a' + '\uff1b'.join(s['excluded']), '']
report += ['## \u516c\u5171\u89c6\u89c9\u7ea6\u675f', '']
for c in model['sharedConstraints']:
    report += ['### ' + c['title'], '', '\u6765\u6e90\uff1a' + c['source'], '']
    report += ['- ' + x for x in c['checks']] + ['']
report += ['## \u539f\u6587\u9a8c\u6536\u70b9\u6620\u5c04', '', '| \u68c0\u67e5\u70b9 | \u5bf9\u5e94\u76ee\u6807 | \u5224\u5b9a\u542b\u4e49 |', '| --- | --- | --- |']
for a in model['acceptance']:
    report.append('| ' + a['id'] + ' ' + a['title'] + ' | ' + readable_target(a['target']) + ' | ' + a['interpretation'] + ' |')
report += ['', '## \u6709\u6765\u6e90\u7684\u62c6\u5206\u4e0e\u5408\u5e76\u51b3\u5b9a', '']
for d in model['decisions']:
    report += ['- ' + d['topic'] + '\uff1a' + d['resolution'] + '\uff08' + d['source'] + '\uff09']
report += ['', '## \u6765\u6e90\u8986\u76d6\u4e0e\u5ba1\u67e5\u72b6\u6001', '',
           '\u9700\u6c42\u6587\u6863\u7b2c1\u20136\u8282\u7684' + str(len(coverage)) + '\u4e2a\u6709\u610f\u4e49\u6761\u76ee\u5747\u767b\u8bb0\u5177\u4f53\u6620\u5c04\u6216\u8303\u56f4\u5904\u7f6e\uff1b\u56fe01\u201323\u5404\u6709\u5bf9\u5e94\u573a\u666f\u4e0e\u533a\u57df\u3002\u7b2c7\u8282\u4e3a\u539f\u6587\u7f16\u5199\u4ea4\u4ed8\u8bf4\u660e\uff0c\u4e0d\u8f6c\u4e3a\u5e94\u7528\u9700\u6c42\u3002\u6620\u5c04\u8bb0\u5f55\u4f4d\u4e8eanalysis.json\u53ca\u53ea\u8bfbreview.html\uff0c\u8fc7\u7a0b\u8bc1\u636e\u89c1_process/evidence/source-coverage.md\u3002', '',
           '\u7ed3\u6784\u68c0\u67e5\u901a\u8fc7\uff1a\u6765\u6e90SHA256\u3001\u5168\u90e8\u753b\u677f\u6620\u5c04\u30012\u00d7\u5c3a\u5bf8\u3001\u8bbe\u8ba1\u6811\u5c3a\u5bf8\u3001\u5c40\u90e8\u8282\u70b9\u5f15\u7528\u548cA01\u2013A08\u6620\u5c04\u3002\u7ed3\u6784\u68c0\u67e5\u4e0d\u8bc1\u660e\u8bed\u4e49\u5b8c\u6574\u6216\u5e94\u7528\u89c6\u89c9\u5bf9\u9f50\u901a\u8fc7\u3002', '',
           '\u72ec\u7acb\u590d\u6838\uff1a' + {'stale_after_contract_correction': '\u4e0a\u6b21\u4ec5\u590d\u6838\u89c6\u89c9\u8d44\u6599\uff0c\u4e0d\u80fd\u4f5c\u4e3a\u5f53\u524d\u89c4\u8303\u5b8c\u6210\u8bc1\u636e', 'completed_with_documented_limitations': '\u5df2\u5b8c\u6210\uff0c\u4fdd\u7559\u8d44\u6599\u9650\u5236', 'pending': '\u5f85\u590d\u6838'}.get(model['review'].get('independent', 'pending'), model['review'].get('independent', 'pending')) + '\uff1b\u4eba\u5de5\u6700\u7ec8\u786e\u8ba4\uff1a\u5f85\u786e\u8ba4\u3002', '',
           '## \u5f85\u51b3\u4e0e\u9650\u5236', '',
           '\n'.join(q['question'] for q in model['questions'] if q['status'] == 'open') or '\u5f53\u524d\u8303\u56f4\u5185\u672a\u53d1\u73b0\u5f85\u6f84\u6e05\u7684\u9700\u6c42\u6b67\u4e49\u3002\u6b64\u524d\u4e1a\u52a1\u5165\u53e3\u4e0e\u8fc1\u79fb\u95ee\u9898\u5df2\u4f5c\u4e3a\u8303\u56f4\u5916\u5173\u95ed\uff1b\u8d44\u6599\u6838\u9a8c\u9650\u5236\u5355\u72ec\u5217\u793a\u3002']
for l in model['limitations']:
    report += ['', '- ' + l['detail'] + ' ' + l['impact']]
report += ['', '## \u9605\u8bfb\u5165\u53e3', '',
           '- review.html\uff1a\u5185\u5d4c23\u5f20\u53c2\u8003\u56fe\uff0c\u6309\u9875\u67e5\u770b\u5f53\u524d\u4e8b\u5b9e\u3001\u5c40\u90e8\u5bf9\u9f50\u76ee\u6807\u3001\u53c2\u6570\u548c\u8fb9\u754c\u3002', '',
           '- analysis.json\uff1a\u5c1a\u672a\u8f6c\u5165\u6b63\u5f0fSchema v2\u7684\u89c6\u89c9\u8d44\u6599\u6574\u7406\uff1b\u4e0d\u80fd\u66ff\u4ee3\u53cc\u56fe\u6a21\u578b\u6216\u4f5c\u4e3a\u5df2\u5b8c\u6210\u9700\u6c42\u5206\u6790\u4ea4\u4ed8\u3002', '']
clarity = model['clarityAssessment']
clarity_report = ['## \u9700\u6c42\u660e\u786e\u6027\u8bc4\u4f30', '', clarity['summary'], '', '| \u7ef4\u5ea6 | \u7ed3\u8bba | \u4f9d\u636e |', '| --- | --- | --- |']
for check in clarity['checks']:
    clarity_report.append('| ' + check['dimension'] + ' | ' + check['conclusion'] + ' | ' + check['source'] + ' |')
clarity_report += ['', '\u8303\u56f4\u5185\u5f85\u6f84\u6e05\u9879\uff1a\u5f53\u524d\u672a\u53d1\u73b0\u3002\u4e1a\u52a1\u5165\u53e3\u4e0e\u9875\u9762\u8fc1\u79fb\u4e0d\u4f5c\u4e3a\u672c\u6b21PRD\u7f3a\u53e3\u3002', '', clarity['methodIssue'], '']
report[4:4] = clarity_report
(RUN / 'analysis.md').write_bytes(('\n'.join(report) + '\n').encode('utf-8'))

payload = copy.deepcopy(model)
payload['tokens'] = tokens
payload['designDetails'] = {s['frameId']: s['nodes'] for s in design['screens']}
for s in payload['scenarios']:
    s['imageData'] = 'data:image/png;base64,' + base64.b64encode((RUN / s['imagePath']).read_bytes()).decode('ascii')
template = (WORK / 'review-template.html').read_text(encoding='utf-8')
safe = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
(RUN / 'review.html').write_bytes(template.replace('__ANALYSIS_DATA__', safe).encode('utf-8'))
manifest = {'modelKind': model['modelKind'], 'semanticDigest': semantic_digest,
            'status': 'incomplete', 'fixedSkillPipeline': 'required_not_completed', 'humanAcceptance': 'pending',
            'files': {name: sha((RUN / name).read_bytes()) for name in ['analysis.json', 'analysis.md', 'review.html']}}
manifest['bundleDigest'] = sha(json.dumps(manifest['files'], sort_keys=True).encode('utf-8'))
write_json(RUN / 'manifest.json', manifest)
state = read('run-state.json')
state.update({'phase': 'incomplete', 'semanticDigest': semantic_digest,
              'nextAction': 'Complete required analysis artifacts within confirmed visual scope; do not request excluded implementation details.',
              'pendingFrames': [], 'waitingForUser': any(q['status'] == 'open' for q in model['questions'])})
write_json(WORK / 'run-state.json', state)
print(json.dumps({'frames': len(model['scenarios']), 'regions': sum(len(s['regions']) for s in model['scenarios']),
                  'sourceItems': len(coverage), 'semanticDigest': semantic_digest,
                  'bundleDigest': manifest['bundleDigest'], 'htmlBytes': (RUN / 'review.html').stat().st_size,
                  'validation': 'passed'}, ensure_ascii=True))
