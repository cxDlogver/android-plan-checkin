"""Deterministic artifact generation and gates for PRD business-fact analysis."""
import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / 'references' / 'model.schema.json'
REVIEW_RULES = {
    'business-facts': 'states', 'observable-states': 'states',
    'source-backed-states': 'states', 'real-operations': 'transitions',
    'atomicity': 'atomicRequirements', 'visual-fields': 'requirements',
    'scope-coverage': 'clauses',
}
LIMITATION = '脚本验证结构、引用和派生一致性；业务事实、操作真实性、原文覆盖与人工作答真实性须逐条阅读来源并完成带证据语义审查。本报告不代表应用已实现或验收通过。'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def digest(m):
    core = {k: v for k, v in m.items() if k not in ('reviews', 'reviewDigest')}
    return hashlib.sha256(canonical(core).encode('utf-8')).hexdigest()


def write_json(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def schema_errors(value, schema, at='$'):
    errors = []
    kinds = {'object': lambda x: isinstance(x, dict), 'array': lambda x: isinstance(x, list),
             'string': lambda x: isinstance(x, str), 'boolean': lambda x: isinstance(x, bool),
             'integer': lambda x: isinstance(x, int) and not isinstance(x, bool)}
    if 'type' in schema and not kinds[schema['type']](value):
        return [at + ': expected ' + schema['type']]
    if 'const' in schema and value != schema['const']:
        errors.append(at + ': incorrect constant')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(at + ': unknown enum value')
    if isinstance(value, str):
        if len(value.strip()) < schema.get('minLength', 0): errors.append(at + ': empty string')
        if 'pattern' in schema and not re.search(schema['pattern'], value): errors.append(at + ': pattern mismatch')
    if isinstance(value, int) and 'minimum' in schema and value < schema['minimum']:
        errors.append(at + ': below minimum')
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        errors += [at + ': missing ' + k for k in schema.get('required', []) if k not in value]
        if schema.get('additionalProperties') is False:
            errors += [at + ': unexpected ' + k for k in value if k not in properties]
        for k, v in value.items():
            if k in properties: errors += schema_errors(v, properties[k], at + '.' + k)
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0): errors.append(at + ': too few items')
        if schema.get('uniqueItems') and len({canonical(x) for x in value}) != len(value):
            errors.append(at + ': duplicate array items')
        for i, v in enumerate(value):
            errors += schema_errors(v, schema.get('items', {}), at + '[' + str(i) + ']')
    return errors


def derived(m):
    head = {k: m[k] for k in ('schemaVersion', 'analysisId', 'revision')}
    head['modelDigest'] = digest(m)
    states = {s['id']: s for s in m['states']}
    transitions = {t['id']: t for t in m['transitions']}
    details = []
    for r in m['atomicRequirements']:
        t = transitions.get(r['transitionId'])
        if t is None or t['from'] not in states or t['to'] not in states:
            raise ValueError('Cannot derive requirement with invalid transition: ' + r['id'])
        details.append({**copy.deepcopy(r), 'sourceState': states[t['from']],
                        'transition': t, 'targetState': states[t['to']]})
    edges = []
    for a in m['atomicRequirements']:
        for b in m['atomicRequirements']:
            ta, tb = transitions[a['transitionId']], transitions[b['transitionId']]
            if ta['to'] == tb['from']:
                edges.append({'from': a['id'], 'to': b['id'], 'viaStateId': ta['to']})
    return {
        'clarification.json': {**head, 'scope': m['scope'], 'items': m['clarifications']},
        'state-graph.json': {**head, 'startStateIds': [s['id'] for s in m['states'] if s['isStart']],
                             'nodes': m['states'], 'edges': m['transitions']},
        'atomic-requirements.json': {**head, 'requirements': details,
                                     'nonTransitionRequirements': m['nonTransitionRequirements']},
        'requirement-graph.json': {**head, 'nodes': [{'id': r['id'], 'name': r['name'],
                                      'transitionId': r['transitionId'],
                                      'functionalRequirements': r['functionalRequirements'],
                                      'visualRequirements': r['visualRequirements']} for r in m['atomicRequirements']],
                                  'edges': edges, 'edgeRule': 'to(Ri) == from(Rj)',
                                  'interpretation': '仅代表业务状态抽象层面的衔接；guard 与实例参数仍需满足。', 'acceptanceScenarios': m['scenarios']},
    }


def esc(x):
    return str(x).replace('|', '&#124;').replace('\n', '<br>')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(esc(v) for v in row) + ' |' for row in rows])


def mermaid_label(x):
    return str(x).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' ')


def markdown(m, exports):
    prefix = '版本：' + str(m['revision']) + '；模型摘要：' + digest(m) + '\n\n'
    fence = chr(96) * 3
    pending = '\n尚在需求澄清阶段，空图仅为结构初始化，不代表正式建模完成。\n' if m['phase'] == 'clarifying' else ''
    clar = '# 需求澄清记录\n\n' + prefix + '## 分析范围\n\n' + m['scope']['objective'] + '\n\n'
    clar += '纳入：' + '；'.join(m['scope']['included']) + '\n\n排除：' + '；'.join(m['scope']['excluded']) + '\n\n'
    for q in m['clarifications']:
        clar += '## ' + q['id'] + ' ' + q['question'] + '\n\n状态：' + q['status'] + '\n\n建议：' + q['proposal']
        clar += '\n\n确认结论：' + (q['resolution'] or '待用户回答')
        clar += '\n\n用户原始回答：' + (q['confirmation']['quote'] or '无')
        clar += '\n\n对话引用：' + (q['confirmation']['conversationRef'] or '无') + '\n\n'
    clar += '## PRD 条款及范围覆盖\n\n' + table(['条款', '位置', '原文', '范围', '覆盖'],
             [(c['id'], c['locator'], c['quote'], c['scope'] + '：' + c['scopeReason'], ', '.join(c['coverageIds'])) for c in m['clauses']]) + '\n'
    diagram = ['flowchart LR']
    for s in m['states']:
        title = s['id'] + ' ' + s['name'] + ('〔起始〕' if s['isStart'] else '')
        diagram.append('  ' + s['id'] + '["' + mermaid_label(title) + '"]')
    for t in m['transitions']:
        diagram.append('  ' + t['from'] + ' -->|"' + mermaid_label(t['id'] + ' ' + t['operation']) + '"| ' + t['to'])
    sg = '# 业务状态转移图\n\n' + prefix + m['scope']['abstraction'] + '\n' + pending + '\n'
    sg += fence + 'mermaid\n' + '\n'.join(diagram) + '\n' + fence + '\n\n'
    for s in m['states']:
        sg += '## ' + s['id'] + ' ' + s['name'] + '\n\n投影与参数：' + s['scope'] + '\n\n'
        sg += '\n'.join('- ' + x for x in s['businessFacts']) + '\n\n验证方法：' + s['verification']['method'] + '\n\n'
        sg += '\n'.join('- ' + x for x in s['verification']['assertions']) + '\n\n来源：' + ', '.join(s['sourceIds']) + '\n\n'
    sg += '## 操作边\n\n' + table(['边', '始态', '操作／主体', '条件', '终态', '结果断言', '来源'],
          [(t['id'], t['from'], t['operation'] + '／' + t['actor'], t['guard'], t['to'], '；'.join(t['effects']), ', '.join(t['sourceIds'])) for t in m['transitions']]) + '\n'
    ar = '# 原子需求\n\n' + prefix + pending + '\n每项恰好对应一个（始态，操作，终态）三元组。\n\n'
    for r in exports['atomic-requirements.json']['requirements']:
        t = r['transition']
        ar += '## ' + r['id'] + ' ' + r['name'] + '\n\n三元组：' + t['from'] + ' → [' + t['id'] + ' ' + t['operation'] + '] → ' + t['to'] + '\n\n'
        ar += requirement_text(r)
    ar += '## 验收链路\n\n'
    for case in m['scenarios']:
        ar += '### ' + case['id'] + ' ' + case['name'] + '\n\n实例绑定：' + case['bindings'] + '\n\n需求序列：' + ' → '.join(case['requirementIds']) + '\n\n预期：' + case['expected'] + '\n\n'
    ar += '## 非迁移要求\n\n交付物与持续质量不伪装成业务事件，不进入需求衔接图。\n\n'
    for r in m['nonTransitionRequirements']:
        ar += '### ' + r['id'] + ' ' + r['name'] + '（' + r['kind'] + '）\n\n' + requirement_text(r)
    rg = '# 原子需求衔接图\n\n' + prefix + '仅当上一个需求终态 ID 等于下一个需求始态 ID 时连边；不表示开发先后。实例参数与 guard 仍需满足。\n' + pending + '\n'
    rd = ['flowchart LR']
    for r in m['atomicRequirements']: rd.append('  ' + r['id'] + '["' + mermaid_label(r['id'] + ' ' + r['name']) + '"]')
    for e in exports['requirement-graph.json']['edges']: rd.append('  ' + e['from'] + ' -->|"' + e['viaStateId'] + '"| ' + e['to'])
    rg += fence + 'mermaid\n' + '\n'.join(rd) + '\n' + fence + '\n\n'
    rg += table(['前项', '后项', '衔接状态'], [(e['from'], e['to'], e['viaStateId']) for e in exports['requirement-graph.json']['edges']]) + '\n'
    return {'clarification.md': clar, 'state-graph.md': sg, 'atomic-requirements.md': ar, 'requirement-graph.md': rg}


def requirement_text(r):
    f, v = r['functionalRequirements'], r['visualRequirements']
    return ('功能需求：' + f['statement'] + '\n\n验收标准：\n\n' + '\n'.join('- ' + x for x in f['acceptanceCriteria']) +
            '\n\n视觉需求（' + v['applicability'] + '）：' + v['reason'] + '\n\n' +
            '\n'.join('- ' + x for x in v['criteria']) + '\n\n来源：' + ', '.join(r['sourceIds']) + '\n\n')


def render(m, model_path):
    errors = schema_errors(m, load(SCHEMA))
    if errors: raise ValueError('\n'.join(errors))
    exports = derived(m)
    folder = Path(model_path).parent
    for name, data in exports.items(): write_json(folder / name, data)
    for name, text in markdown(m, exports).items(): (folder / name).write_text(text, encoding='utf-8')


def gate(m, model_path, check_artifacts=True):
    checks = []
    def add(check_id, errors, blocked=False):
        checks.append({'id': check_id, 'result': ('BLOCKED' if blocked else 'FAIL') if errors else 'PASS', 'issues': errors})
    errors = schema_errors(m, load(SCHEMA))
    add('schema', errors)
    if errors:
        return {'result': 'FAIL', 'modelDigest': digest(m), 'checks': checks, 'limitation': LIMITATION}
    collections = ['sources', 'clauses', 'clarifications', 'states', 'transitions', 'atomicRequirements', 'nonTransitionRequirements', 'scenarios']
    all_ids = [x['id'] for key in collections for x in m[key]]
    add('unique-ids', [k for k, n in Counter(all_ids).items() if n > 1] + [i for i in all_ids if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', i)])
    source_map = {s['id']: s for s in m['sources']}
    source_texts, src_errors = {}, []
    for s in m['sources']:
        p = Path(model_path).parent / s['path']
        try:
            raw = p.read_bytes()
            if hashlib.sha256(raw).hexdigest() != s['sha256']: src_errors.append(s['id'] + ': source hash changed')
            source_texts[s['id']] = raw.decode('utf-8')
        except (OSError, UnicodeError) as e: src_errors.append(s['id'] + ': ' + str(e))
    for c in m['clauses']:
        if c['sourceId'] not in source_texts: src_errors.append(c['id'] + ': unknown/unreadable source')
        elif c['quote'] not in source_texts[c['sourceId']]: src_errors.append(c['id'] + ': quote not present in source')
    add('source-integrity', src_errors)
    pending = [q['id'] + ': unanswered clarification' for q in m['clarifications'] if q['status'] == 'open']
    if m['phase'] != 'review_ready': pending.append('phase is not review_ready')
    add('clarification', pending, True)
    add('confirmation-records', [q['id'] + ': missing actual resolution/quote/reference' for q in m['clarifications'] if q['status'] != 'open' and
        not all([q['resolution'].strip(), q['confirmation']['quote'].strip(), q['confirmation']['conversationRef'].strip()])])
    state_map = {s['id']: s for s in m['states']}
    transition_map = {t['id']: t for t in m['transitions']}
    starts = [s['id'] for s in m['states'] if s['isStart']]
    graph_errors = []
    if not starts: graph_errors.append('No business start state')
    if not m['transitions']: graph_errors.append('No business operation')
    for t in m['transitions']:
        for k in ('from', 'to'):
            if t[k] not in state_map: graph_errors.append(t['id'] + ': unknown ' + k)
    seen, queue = set(starts), deque(starts)
    while queue:
        at = queue.popleft()
        for t in m['transitions']:
            if t['from'] == at and t['to'] in state_map and t['to'] not in seen:
                seen.add(t['to']); queue.append(t['to'])
    graph_errors += [s + ': unreachable state' for s in state_map if s not in seen]
    incident = {t[k] for t in m['transitions'] for k in ('from', 'to')}
    graph_errors += [s + ': no operation relates to state' for s in state_map if s not in incident]
    add('business-graph', graph_errors)
    included = {c['id'] for c in m['clauses'] if c['scope'] == 'included'}
    confirmed = {q['id'] for q in m['clarifications'] if q['status'] == 'confirmed'}
    valid_refs = included | confirmed
    ref_errors = []
    entities = m['states'] + m['transitions'] + m['atomicRequirements'] + m['nonTransitionRequirements']
    for e in entities:
        if not included.intersection(e['sourceIds']): ref_errors.append(e['id'] + ': no included PRD clause')
        ref_errors += [e['id'] + ': unsupported source ' + x for x in e['sourceIds'] if x not in valid_refs]
    add('business-source-trace', ref_errors)
    atom_errors = []
    counts = Counter(r['transitionId'] for r in m['atomicRequirements'])
    for t in m['transitions']:
        if counts[t['id']] != 1: atom_errors.append(t['id'] + ': must have exactly one atomic requirement')
    for r in m['atomicRequirements']:
        if r['transitionId'] not in transition_map: atom_errors.append(r['id'] + ': transition missing')
    add('one-transition-one-requirement', atom_errors)
    reqs = m['atomicRequirements'] + m['nonTransitionRequirements']
    by_req = {r['id']: r for r in reqs}
    cover_errors = []
    if not included: cover_errors.append('No included PRD clauses')
    for c in m['clauses']:
        if c['scope'] == 'included' and not c['coverageIds']: cover_errors.append(c['id'] + ': uncovered clause')
        if c['scope'] != 'included' and c['coverageIds']: cover_errors.append(c['id'] + ': excluded/context clause has requirement coverage')
        for rid in c['coverageIds']:
            if rid not in by_req: cover_errors.append(c['id'] + ': unknown coverage ' + rid)
            elif c['id'] not in by_req[rid]['sourceIds']: cover_errors.append(c['id'] + ': coverage has no reverse source link ' + rid)
    for r in reqs:
        for cid in included.intersection(r['sourceIds']):
            clause = next(c for c in m['clauses'] if c['id'] == cid)
            if r['id'] not in clause['coverageIds']: cover_errors.append(r['id'] + ': absent from clause coverage ' + cid)
    add('prd-coverage', cover_errors)
    scenario_errors = []
    for case in m['scenarios']:
        sequence = []
        for rid in case['requirementIds']:
            r = by_req.get(rid)
            if r is None or 'transitionId' not in r or r['transitionId'] not in transition_map:
                scenario_errors.append(case['id'] + ': invalid atomic requirement ' + rid)
            else: sequence.append(transition_map[r['transitionId']])
        for left, right in zip(sequence, sequence[1:]):
            if left['to'] != right['from']:
                scenario_errors.append(case['id'] + ': disconnected acceptance sequence')
        if not included.intersection(case['sourceIds']) or any(x not in valid_refs for x in case['sourceIds']):
            scenario_errors.append(case['id'] + ': invalid scenario source')
    add('acceptance-sequences', scenario_errors)
    visual_errors = []
    for r in reqs:
        v = r['visualRequirements']
        if v['applicability'] == 'required' and not v['criteria']: visual_errors.append(r['id'] + ': missing visual criteria')
        if v['applicability'] == 'not_applicable' and v['criteria']: visual_errors.append(r['id'] + ': not_applicable must not contain visual criteria')
    add('functional-visual-fields', visual_errors)
    review_errors = []
    expected = {key: {e['id'] for e in (reqs if coll == 'requirements' else m[coll])} for key, coll in REVIEW_RULES.items()}
    for key, ids in expected.items():
        relevant = [r for r in m['reviews'] if r['ruleId'] == key]
        checked = {i for r in relevant if r['result'] == 'pass' for i in r['entityIds']}
        if not relevant: review_errors.append(key + ': missing semantic review')
        if checked != ids: review_errors.append(key + ': review entities must exactly cover expected entities')
        for r in relevant:
            if r['result'] != 'pass': review_errors.append(key + ': review has a failure')
    if m['reviewDigest'] != digest(m): review_errors.append('reviewDigest is stale or missing')
    add('semantic-review', review_errors)
    if check_artifacts:
        artifact_errors = []
        try:
            exports = derived(m)
            for name, expected_data in exports.items():
                try:
                    actual = load(Path(model_path).parent / name)
                    if actual != expected_data: artifact_errors.append(name + ': data drift')
                except (OSError, ValueError) as e: artifact_errors.append(name + ': ' + str(e))
            for name, text in markdown(m, exports).items():
                try:
                    if (Path(model_path).parent / name).read_text(encoding='utf-8') != text: artifact_errors.append(name + ': document drift')
                except OSError as e: artifact_errors.append(name + ': ' + str(e))
        except (KeyError, ValueError) as e: artifact_errors.append(str(e))
        add('complete-synchronized-artifacts', artifact_errors)
    result = 'BLOCKED' if pending else ('FAIL' if any(x['result'] == 'FAIL' for x in checks) else 'PASS')
    return {'schemaVersion': m['schemaVersion'], 'analysisId': m['analysisId'], 'revision': m['revision'],
            'modelDigest': digest(m), 'result': result,
            'counts': {'states': len(m['states']), 'transitions': len(m['transitions']),
                       'atomicRequirements': len(m['atomicRequirements']), 'nonTransitionRequirements': len(m['nonTransitionRequirements'])},
            'checks': checks, 'limitation': LIMITATION}


def save_report(report, folder):
    write_json(Path(folder) / 'gate-report.json', report)
    lines = ['# 需求分析门禁报告', '', '结果：**' + report['result'] + '**', '',
             '模型摘要：' + report['modelDigest'], '', report['limitation'], '',
             table(['检查', '结果', '问题'], [(c['id'], c['result'], '；'.join(c['issues']) or '无') for c in report['checks']])]
    if 'counts' in report: lines += ['', '数量：' + canonical(report['counts'])]
    (Path(folder) / 'gate-report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def initialize(folder, prd, analysis_id):
    folder = Path(folder).resolve(); folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'analysis-model.json'
    if target.exists(): raise ValueError('Refusing to overwrite existing model')
    prd = Path(prd).resolve()
    import os
    m = {'schemaVersion': 1, 'analysisId': analysis_id, 'revision': 1, 'phase': 'clarifying',
         'scope': {'objective': '读取指定 PRD 并澄清后建立业务事实模型', 'included': ['待 PRD 澄清'],
                   'excluded': [], 'abstraction': '澄清未完成，尚未建立正式业务状态'},
         'sources': [{'id': 'DOC_PRD', 'path': Path(os.path.relpath(prd, folder)).as_posix(),
                      'sha256': hashlib.sha256(prd.read_bytes()).hexdigest()}],
         'clauses': [], 'clarifications': [], 'states': [], 'transitions': [], 'atomicRequirements': [],
         'nonTransitionRequirements': [], 'scenarios': [], 'reviews': [], 'reviewDigest': ''}
    write_json(target, m); render(m, target); save_report(gate(m, target), folder)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    ini = sub.add_parser('init'); ini.add_argument('folder'); ini.add_argument('--prd', required=True); ini.add_argument('--analysis-id', required=True)
    for name in ('render', 'digest', 'gate'):
        s = sub.add_parser(name); s.add_argument('model')
    args = p.parse_args()
    try:
        if args.cmd == 'init': print(initialize(args.folder, args.prd, args.analysis_id)); return 0
        model_path = Path(args.model); m = load(model_path)
        if args.cmd == 'digest': print(digest(m)); return 0
        if args.cmd == 'render': render(m, model_path); print('Artifacts rendered'); return 0
        report = gate(m, model_path); save_report(report, model_path.parent)
        print(json.dumps({'result': report['result'], 'counts': report.get('counts'), 'issues': [c for c in report['checks'] if c['result'] != 'PASS']}, ensure_ascii=False))
        return 0 if report['result'] == 'PASS' else 2
    except (OSError, ValueError, KeyError) as e:
        print(str(e), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
