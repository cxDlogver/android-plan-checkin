"""Staged requirements analysis. Standard library only; no browser automation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from feasibility import analyze
from path_context import paths_for_start, validate_context
from requirement_graph import requirement_graph, verify_coverage, check_context

SKILL = Path(__file__).resolve().parents[1]
ASSETS = SKILL / 'assets'
CONTRACT = json.loads((ASSETS / 'gates.template.json').read_text(encoding='utf-8'))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract_digest(stage):
    files = ['assets/gates.template.json', 'scripts/analyze.py', 'SKILL.md']
    if stage == 'state':
        files += ['references/01-state-graph.md', 'assets/state.schema.json',
                  'scripts/path_context.py', 'scripts/feasibility.py',
                  'scripts/requirement_graph.py', 'scripts/feasible_routes.py',
                  'references/04-final-gate.md']
    elif stage == 'requirements':
        files += ['references/02-requirements.md', 'assets/requirements.schema.json',
                  'scripts/requirement_graph.py', 'scripts/feasible_routes.py',
                  'scripts/path_context.py', 'scripts/feasibility.py', 'references/04-final-gate.md']
    elif stage == 'html':
        files += ['references/03-html.md', 'assets/review.html', 'scripts/render_review.py']
    else:
        files += ['references/04-final-gate.md']
    return digest({name: file_digest(SKILL / name) for name in files})


def schema_errors(value, schema, where='$'):
    """Check the subset used by bundled JSON Schemas, not arbitrary schemas."""
    errors = []
    kind = schema.get('type')
    valid_type = {'object': isinstance(value, dict), 'array': isinstance(value, list),
                  'string': isinstance(value, str),
                  'integer': isinstance(value, int) and not isinstance(value, bool)}
    if kind and not valid_type.get(kind, False):
        return [where + ': expected ' + kind]
    if 'enum' in schema and not any(value == option and type(value) is type(option) for option in schema['enum']):
        errors.append(where + ': invalid value')
    if isinstance(value, str) and len(value.strip()) < schema.get('minLength', 0):
        errors.append(where + ': nonempty text required')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                errors.append(where + ': missing ' + key)
        for key, child in schema.get('properties', {}).items():
            if key in value:
                errors += schema_errors(value[key], child, where + '.' + key)
    if kind == 'array':
        if len(value) < schema.get('minItems', 0):
            errors.append(where + ': too few items')
        for i, child in enumerate(value):
            errors += schema_errors(child, schema.get('items', {}), where + '[' + str(i) + ']')
    return errors


def result_check(rule, errors=None, pending=None):
    return {'id': rule, 'status': 'failed' if errors else 'pending' if pending else 'passed',
            'details': errors or ([pending] if pending else [])}


def report_checks(stage, report_path, input_digest, analyzer_context, targets):
    ids = CONTRACT[stage]['semantic']
    def pending(reason):
        return [result_check(i, pending=reason) for i in ids]
    def failed(reason):
        return [result_check(i, [reason]) for i in ids]
    try:
        report = load(report_path)
    except (OSError, ValueError):
        return pending('independent report missing or unreadable')
    if not isinstance(report, dict) or report.get('stage') != stage or (
            report.get('inputDigest') != input_digest or report.get('contractDigest') != contract_digest(stage)):
        return pending('report input or rule digest is stale')
    if not text(analyzer_context) or report.get('analyzerContext') != analyzer_context:
        return pending('registered actual analyzer context must match the report')
    reviewer = report.get('reviewer', {})
    if not isinstance(reviewer, dict) or reviewer.get('independent') is not True or not text(reviewer.get('context')):
        return pending('actual independent context reference required')
    if reviewer['context'].strip() == analyzer_context.strip():
        return failed('analyzer and reviewer must use different actual contexts')
    rows = report.get('criteria', [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) or not text(r.get('id')) for r in rows) or (
            sorted(r['id'] for r in rows) != sorted(ids)):
        return pending('report must cover exactly the stage semantic criteria')
    sources = report.get('sourceIds')
    if not isinstance(sources, list) or any(not text(s) for s in sources) or sorted(sources) != targets['sourceIds']:
        return pending('review must cover exactly all current source IDs')
    objects = report.get('objects')
    if not isinstance(objects, list) or any(not isinstance(r, dict) or not text(r.get('id')) for r in objects) or (
            sorted(r['id'] for r in objects) != targets['objectIds']):
        return pending('review must cover every current object exactly once')
    closure = report.get('closure')
    if not isinstance(closure, dict) or not isinstance(closure.get('openItems'), list) or not text(closure.get('reason')):
        return pending('current closure reason and remaining analysis items required')
    if closure['openItems']:
        return failed('review has remaining analysis items')
    if isinstance(report.get('findings'), list) and report['findings']:
        return failed('unresolved independent review findings')
    if report.get('findings') != []:
        return pending('current unresolved findings list required')
    def grounded(evidence):
        return isinstance(evidence, list) and bool(evidence) and all(
            isinstance(e, dict) and e.get('sourceId') in targets['sourceIds'] and text(e.get('locator'))
            for e in evidence)
    for row in objects:
        if row.get('status') == 'failed':
            return failed(row['id'] + ': ' + (row.get('reason') or 'object review failed'))
        if row.get('status') != 'passed' or not text(row.get('reason')) or not grounded(row.get('evidence')):
            return pending(row['id'] + ': per-object conclusion and precise source evidence required')
    checks = []
    for row in rows:
        if row.get('status') == 'failed':
            checks.append(result_check(row['id'], [row.get('reason') or 'criterion failed']))
        elif row.get('status') != 'passed' or not text(row.get('reason')) or not grounded(row.get('evidence')):
            checks.append(result_check(row['id'], pending='grounded criterion evidence required'))
        else:
            checks.append({**result_check(row['id']), 'reason': row['reason'], 'evidence': row['evidence']})
    return checks


def analyzer_context(run):
    try:
        value = load(run / '_process/analysis-context.json').get('context')
        return value if text(value) else ''
    except (OSError, ValueError, AttributeError):
        return ''


def review_targets(state, requirements=None):
    objects = state['states'] + state['transitions'] if requirements is None else requirements['requirements']
    return {'objectIds': sorted(row['id'] for row in objects),
            'sourceIds': sorted(row['id'] for row in state['sources'])}

def finish(stage, input_digest, checks, derived=None):
    statuses = {c['status'] for c in checks}
    result = {'stage': stage, 'inputDigest': input_digest, 'contractDigest': contract_digest(stage),
              'status': 'failed' if 'failed' in statuses else 'pending' if 'pending' in statuses else 'passed',
              'checks': checks}
    if derived is not None:
        result['derived'] = derived
    return result


def text(value):
    return isinstance(value, str) and bool(value.strip())


def state_input_digest(run, state):
    evidence = {'analyzerContext': analyzer_context(run)}
    for source in state.get('sources', []):
        try:
            location = run / source['uri']
            if location.is_file():
                evidence['source:' + source['id']] = file_digest(location)
        except (OSError, ValueError, KeyError, TypeError):
            pass  # Remote sources remain bound by their recorded content summary/version.
    evidence.update(preview_fingerprints(run, [ref for row in state['states'] for ref in row['ui']['refs']]))
    document = state.get('clarificationDocument')
    if document:
        try:
            evidence['clarificationDocument'] = file_digest(run / document)
        except (OSError, ValueError):
            evidence['clarificationDocument'] = 'missing'
    return digest({'state': state, 'localEvidence': evidence})


def preview_fingerprints(run, refs):
    fingerprints = {}
    for ref in refs:
        name = ref.get('previewPath')
        if name:
            try:
                fingerprints['preview:' + name] = file_digest(run / name)
            except (OSError, ValueError):
                fingerprints['preview:' + name] = 'missing'
    return fingerprints


def ref_errors(refs, sources, where):
    return [where + ': unknown source ' + str(ref.get('sourceId'))
            for ref in refs if ref.get('sourceId') not in sources]


def state_links(state):
    errors = []
    all_ids = []
    for group in ['sources', 'features', 'states', 'transitions', 'clarifications']:
        all_ids += [r['id'] for r in state[group]]
    if len(all_ids) != len(set(all_ids)):
        errors.append('entity IDs must be unique')
    sources = {r['id'] for r in state['sources']}
    features = {r['id'] for r in state['features']}
    states = {r['id'] for r in state['states']}
    transitions = {r['id'] for r in state['transitions']}
    roots = state['entryStateIds']
    if len(roots) != len(set(roots)) or not set(roots) <= states:
        errors.append('documented entries must be unique known states')
    for row in state['features'] + state['states'] + state['transitions']:
        where = row['id']
        if not set(row['sourceIds']) <= sources:
            errors.append(where + ': unknown source')
        if 'featureIds' in row and not set(row['featureIds']) <= features:
            errors.append(where + ': unknown feature')
    for row in state['states']:
        ui = row['ui']
        errors += ref_errors(ui['refs'], sources, row['id'])
        for constraint in ui['constraints']:
            if not set(constraint['sourceIds']) <= sources:
                errors.append(row['id'] + ': visual constraint has unknown source')
        if ui['applicability'] == 'unknown':
            errors.append(row['id'] + ': visual applicability unresolved')
        elif ui['applicability'] == 'not_applicable' and (
                not text(ui['reason']) or ui['refs'] or ui['constraints']):
            errors.append(row['id'] + ': not_applicable UI requires a reason and empty obligations')
        elif ui['applicability'] == 'applicable' and not (ui['refs'] or ui['constraints']):
            errors.append(row['id'] + ': applicable UI requires grounded obligations')
    for row in state['transitions']:
        if row['from'] not in states or row['to'] not in states:
            errors.append(row['id'] + ': unknown state endpoint')
        evidence = row.get('selfLoopEvidence')
        if row['from'] == row['to']:
            if not evidence or not evidence['sourceRefs']:
                errors.append(row['id'] + ': self-loop requires source, obligation and state reason')
            else:
                errors += ref_errors(evidence['sourceRefs'], set(row['sourceIds']), row['id'])
        elif evidence:
            errors.append(row['id'] + ': self-loop evidence on a non-loop')
    for row in state['coverage']:
        if row['sourceId'] not in sources or not set(row['stateIds']) <= states or (
                not set(row['transitionIds']) <= transitions):
            errors.append('coverage references unknown entities')
        if row['disposition'] == 'mapped' and not (row['stateIds'] or row['transitionIds']):
            errors.append('mapped obligation has no state or transition')
        if row['disposition'] != 'mapped' and not text(row['reason']):
            errors.append('excluded obligation requires its scope reason')
    if {r['sourceId'] for r in state['coverage']} != sources:
        errors.append('every source needs an obligation disposition; semantic review checks completeness')
    for row in state['clarifications']:
        if not set(row['affectedIds']) <= set(all_ids) | {'scope'}:
            errors.append(row['id'] + ': unknown clarification target')
    if not errors:
        errors += validate_context(state)
    return errors


def state_gate(run, state, review_path):
    shape = schema_errors(state, load(ASSETS / 'state.schema.json'))
    input_digest = state_input_digest(run, state) if not shape else digest(state)
    checks = [result_check('S-STRUCT', shape)]
    derived = {}
    if shape:
        checks += [result_check(i, pending='repair state structure first')
                   for i in ['S-LINKS', 'S-PATHS', 'S-CLARIFY']]
    else:
        links = state_links(state)
        checks.append(result_check('S-LINKS', links))
        clarification_errors = []
        for row in state['clarifications']:
            if row['status'] != 'resolved' or not text(row['resolution']) or not text(row['humanReference']):
                clarification_errors.append(row['id'] + ': unresolved or missing actual human answer reference')
        if state['clarifications']:
            try:
                document = (run / state.get('clarificationDocument', '')).read_text(encoding='utf-8-sig')
                if not document.strip():
                    clarification_errors.append('clarification document is empty')
            except (OSError, ValueError):
                clarification_errors.append('readable clarification confirmation document required')
        checks.append(result_check('S-CLARIFY', clarification_errors))
        if links:
            checks.append(result_check('S-PATHS', pending='repair references or state definitions first'))
        else:
            try:
                validation = analyze(state)
                computed = {r: paths_for_start(state, r) for r in state['entryStateIds']}
                paths = {r: result[0] for r, result in computed.items()}
                unreachable = [s['id'] for s in state['states']
                               if all(rows[s['id']] is None for rows in paths.values())]
                path_conditions = {entry: {sid: check_context(state, {'entryStateId': entry, 'transitionIds': tids})
                    for sid, tids in rows.items() if tids is not None} for entry, rows in paths.items()}
                derived = {'pathsByEntry': paths, 'pathConditionsByEntry': path_conditions,
                           'pathChecks': {r: v[1] for r, v in computed.items()},
                           'transitionValidation': validation}
                errors = ['unreachable retained states: ' + ', '.join(unreachable)] if unreachable else []
                if validation['status'] == 'failed':
                    errors.append('a declared transition or condition case has no feasible entry witness')
                checks.append(result_check('S-PATHS', errors, pending=(
                    'condition abstraction or witness search incomplete' if validation['status'] == 'incomplete' else None)))
            except ValueError as exc:
                checks.append(result_check('S-PATHS', pending=str(exc)))
    actor = analyzer_context(run)
    targets = review_targets(state) if not shape else {'objectIds': [], 'sourceIds': []}
    checks += report_checks('state', review_path, input_digest, actor, targets)
    result = finish('state', input_digest, checks, derived)
    result.update(analyzerContext=actor, reviewTargets=targets)
    return result


def model_for(state, requirements):
    model = copy.deepcopy(state)
    model['requirements'] = requirements['requirements']
    model['requirementTraversal'] = requirements['requirementTraversal']
    by_transition = {r['transitionId']: r['id'] for r in requirements['requirements']}
    for transition in model['transitions']:
        transition['requirementId'] = by_transition[transition['id']]
    return model


def mapping_errors(state, requirements):
    errors = []
    sources = {r['id'] for r in state['sources']}
    transitions = {r['id']: r for r in state['transitions']}
    rows = requirements['requirements']
    if len({r['id'] for r in rows}) != len(rows):
        errors.append('requirement IDs must be unique')
    upstream_ids = {r['id'] for group in ['sources', 'features', 'states', 'transitions', 'clarifications'] for r in state[group]}
    if any(r['id'] in upstream_ids for r in rows):
        errors.append('requirement IDs must not collide with upstream entity IDs')
    if len(rows) != len(transitions) or {r['transitionId'] for r in rows} != set(transitions):
        errors.append('exactly one atomic requirement per state transition required')
    for row in rows:
        transition = transitions.get(row['transitionId'])
        if transition is None:
            continue
        if set(row['featureIds']) != set(transition['featureIds']):
            errors.append(row['id'] + ': feature attribution differs from transition')
        if not set(row['sourceIds']) <= sources or not set(transition['sourceIds']) <= set(row['sourceIds']):
            errors.append(row['id'] + ': source mapping must preserve transition sources')
        if all(row[k]['applicability'] != 'applicable' for k in ['functionalAcceptance', 'visualAcceptance']):
            errors.append(row['id'] + ': at least one grounded acceptance obligation required')
        for field in ['functionalAcceptance', 'visualAcceptance']:
            facet = row[field]
            if facet['applicability'] == 'unknown':
                errors.append(row['id'] + ': acceptance applicability unresolved')
            if facet['applicability'] == 'not_applicable' and (not text(facet['reason']) or facet['checks']):
                errors.append(row['id'] + ': not_applicable facet needs a reason and empty checks')
            if facet['applicability'] == 'applicable' and not facet['checks']:
                errors.append(row['id'] + ': applicable facet needs checks')
            for check in facet['checks']:
                if not set(check['sourceIds']) <= sources:
                    errors.append(row['id'] + ': acceptance has unknown source')
                errors += ref_errors(check.get('uiRefs', []), sources, row['id'])
                if field == 'visualAcceptance' and not check.get('uiRefs'):
                    errors.append(row['id'] + ': visual check needs a precise UI/text specification reference')
    return errors


def derive_graph(state, requirements):
    graph = requirement_graph(model_for(state, requirements))
    if graph['traversal'].get('algorithm') != 'witness_cover':
        complete = graph['traversal']['status'] == 'optimal' and all(
            r['contextCheck']['status'] in {'finite_domain_passed', 'no_guard_constraints'}
            for r in graph['traversal']['routes'])
        graph['traversal']['optimality'] = 'proven' if complete else 'not_proven'
    return graph


def requirements_gate(state, requirements, state_result, review_path, run=None):
    shape = schema_errors(requirements, load(ASSETS / 'requirements.schema.json'))
    media = {}
    if not shape and run is not None:
        media = preview_fingerprints(run, [ref for row in requirements['requirements']
            for check in row['visualAcceptance']['checks'] for ref in check.get('uiRefs', [])])
    input_digest = digest({'stateInputDigest': state_result['inputDigest'], 'requirements': requirements, 'localEvidence': media})
    if not isinstance(requirements, dict) or requirements.get('stateDigest') != digest(state):
        shape.append('stateDigest differs from current state graph')
    checks = [result_check('R-STRUCT', shape)]
    if state_result['status'] != 'passed':
        checks.append(result_check('R-MAPPING', pending='current state gate must pass first'))
        checks.append(result_check('R-GRAPH', pending='current state gate must pass first'))
    elif shape:
        checks += [result_check(i, pending='repair requirement structure first') for i in ['R-MAPPING', 'R-GRAPH']]
    else:
        mapping = mapping_errors(state, requirements)
        checks.append(result_check('R-MAPPING', mapping))
        if mapping:
            checks.append(result_check('R-GRAPH', pending='repair transition mapping first'))
        else:
            try:
                expected = derive_graph(state, requirements)
                graph = requirements['graph']
                errors = [] if graph == expected else ['graph differs from deterministic route derivation; run --derive']
                errors += verify_coverage(model_for(state, requirements), expected)
                if expected['reduction']['uncoveredRequirementIds']:
                    errors.append('not all atomic requirements have feasible continuous coverage')
                if any(r['contextCheck']['status'] not in {'finite_domain_passed', 'no_guard_constraints'}
                       for r in expected['traversal']['routes']):
                    errors.append('route condition conflict or incomplete abstraction')
                checks.append(result_check('R-GRAPH', errors))
            except ValueError as exc:
                checks.append(result_check('R-GRAPH', [str(exc)]))
    actor = state_result.get('analyzerContext', '')
    targets = review_targets(state, requirements) if not shape else {'objectIds': [], 'sourceIds': []}
    checks += report_checks('requirements', review_path, input_digest, actor, targets)
    result = finish('requirements', input_digest, checks)
    result.update(analyzerContext=actor, reviewTargets=targets)
    return result


def html_gate(run, state, requirements, state_result, req_result, html_path, generate=False):
    from render_review import presentation, render, extract_payload
    inputs = {'state': state, 'requirements': requirements}
    input_digest = digest(inputs)
    if state_result['status'] != 'passed' or req_result['status'] != 'passed':
        return finish('html', input_digest, [result_check(i, pending='first two gates must pass')
                                            for i in CONTRACT['html']['mechanical']])
    try:
        payload = presentation(run, state, requirements, state_result['derived'])
        expected = render(payload)
        if generate:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(expected, encoding='utf-8')
        actual = html_path.read_text(encoding='utf-8')
        data_errors = [] if extract_payload(actual) == payload else ['embedded data differs from accepted inputs']
        template_errors = [] if actual == expected else ['HTML differs from current deterministic template output']
        checks = [result_check('H-INPUT'), result_check('H-DATA', data_errors),
                  result_check('H-TEMPLATE', template_errors)]
        result = finish('html', input_digest, checks)
        result.update({'htmlDigest': file_digest(html_path), 'browserVerification': 'not_performed_static_only'})
        return result
    except FileNotFoundError as exc:
        return finish('html', input_digest, [result_check('H-INPUT'),
                      result_check('H-DATA', pending=str(exc)), result_check('H-TEMPLATE', pending='HTML or preview not yet available')])
    except (OSError, ValueError, KeyError) as exc:
        return finish('html', input_digest, [result_check('H-INPUT'),
                      result_check('H-DATA', [str(exc)]), result_check('H-TEMPLATE', pending='repair HTML inputs first')])


def initialize(run, context=None):
    run.mkdir(parents=True, exist_ok=True)
    process = run / '_process'
    process.mkdir(exist_ok=True)
    if text(context):
        save(process / 'analysis-context.json', {'context': context})
    for name, template in [('state-graph.json', 'state.template.json'), ('requirements.json', 'requirements.template.json')]:
        if not (run / name).exists():
            save(run / name, load(ASSETS / template))
    gates = {stage: {'status': 'pending', 'checks': [result_check(i, pending='not checked')
             for i in value['mechanical'] + value['semantic']]} for stage, value in CONTRACT.items()}
    if not (process / 'gates.json').exists():
        save(process / 'gates.json', gates)
    for stage in ['state', 'requirements']:
        target = process / (stage + '-review.json')
        if not target.exists():
            save(target, {'stage': stage, 'inputDigest': '', 'contractDigest': '',
                         'analyzerContext': analyzer_context(run), 'sourceIds': [], 'objects': [],
                         'closure': {'openItems': [], 'reason': ''},
                         'reviewer': {'independent': False, 'context': ''},
                         'criteria': [{'id': i, 'status': 'pending', 'reason': '', 'evidence': []}
                                      for i in CONTRACT[stage]['semantic']], 'findings': []})


def remember(run, stage, result):
    save(run / '_process' / (stage + '-check.json'), result)
    target = run / '_process/gates.json'
    plan = load(target) if target.exists() else {}
    plan[stage] = {k: v for k, v in result.items() if k != 'derived'}
    save(target, plan)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'state', 'requirements', 'html', 'final'])
    parser.add_argument('run', type=Path)
    parser.add_argument('--state', type=Path, help='override state JSON path, relative to RUN unless absolute')
    parser.add_argument('--requirements', type=Path, help='override requirements JSON path')
    parser.add_argument('--state-review', type=Path, help='override state independent report path')
    parser.add_argument('--requirements-review', type=Path, help='override requirement independent report path')
    parser.add_argument('--html', type=Path, help='override HTML path')
    parser.add_argument('--analyzer-context', help='actual analyzer session/agent reference; stored for independence checks')
    parser.add_argument('--derive', action='store_true', help='derive graph for the requirements command')
    args = parser.parse_args()
    run = args.run.resolve()
    if args.command == 'init':
        initialize(run, args.analyzer_context)
        print(json.dumps({'status': 'initialized', 'run': str(run)}, ensure_ascii=True))
        return 0
    def location(value, default):
        return run / (value or default)
    try:
        if args.analyzer_context is not None:
            if not text(args.analyzer_context):
                raise ValueError('actual analyzer context must be nonempty')
            save(run / '_process/analysis-context.json', {'context': args.analyzer_context})
        state_path = location(args.state, 'state-graph.json')
        req_path = location(args.requirements, 'requirements.json')
        state_review = location(args.state_review, '_process/state-review.json')
        req_review = location(args.requirements_review, '_process/requirements-review.json')
        html_path = location(args.html, 'review.html')
        state = load(state_path)
        if not isinstance(state, dict):
            raise ValueError('state JSON must be an object')
        state_result = state_gate(run, state, state_review)
        remember(run, 'state', state_result)
        if args.command == 'state':
            result = state_result
        else:
            requirements = load(req_path)
            if not isinstance(requirements, dict):
                raise ValueError('requirements JSON must be an object')
            if args.command == 'requirements' and args.derive:
                if state_result['status'] != 'passed':
                    raise ValueError('derive blocked: current state gate must pass')
                candidate = copy.deepcopy(requirements)
                candidate['stateDigest'] = digest(state)
                errors = schema_errors(candidate, load(ASSETS / 'requirements.schema.json'))
                if not errors:
                    errors = mapping_errors(state, candidate)
                if errors:
                    raise ValueError('; '.join(errors))
                candidate['graph'] = derive_graph(state, candidate)
                save(req_path, candidate)
                requirements = candidate
            req_result = requirements_gate(state, requirements, state_result, req_review, run)
            remember(run, 'requirements', req_result)
            if args.command == 'requirements':
                result = req_result
            else:
                html_result = html_gate(run, state, requirements, state_result, req_result, html_path,
                                        generate=args.command == 'html')
                remember(run, 'html', html_result)
                if args.command == 'html':
                    result = html_result
                else:
                    stages = [state_result, req_result, html_result]
                    stage_statuses = {r['status'] for r in stages}
                    stage_check = result_check('F-STAGES', ['one or more stage gates failed'] if 'failed' in stage_statuses else None,
                                               pending='one or more stage gates pending' if 'pending' in stage_statuses else None)
                    state_matches = requirements.get('stateDigest') == digest(state)
                    consistency_errors = ['state binding differs from current JSON'] if not state_matches else (
                        ['HTML data or template differs from current input'] if html_result['status'] == 'failed' else [])
                    consistency_pending = 'HTML chain has not completed' if html_result['status'] == 'pending' else None
                    result = finish('final', digest({'state': state, 'requirements': requirements}), [
                        stage_check, result_check('F-CONSISTENCY', consistency_errors, consistency_pending)])
                    result['stages'] = [{k: v for k, v in r.items() if k != 'derived'} for r in stages]
                    result['files'] = {str(p): file_digest(p) for p in [state_path, req_path, html_path] if p.is_file()}
                    result['limitations'] = ['HTML checked statically; no real browser acceptance.']
                    if isinstance(requirements.get('graph'), dict):
                        result['optimality'] = requirements['graph'].get('traversal', {}).get('optimality', 'unknown')
                    save(run / 'gate-result.json', result)
                    remember(run, 'final', result)
        print(json.dumps({k: v for k, v in result.items() if k not in {'derived', 'stages'}}, ensure_ascii=True))
        return 0 if result['status'] == 'passed' else 2 if result['status'] == 'pending' else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {'stage': args.command, 'status': 'pending' if isinstance(exc, FileNotFoundError) else 'failed', 'error': str(exc),
                  'repairFrom': 'restore valid inputs; rerun the affected stage'}
        remember(run, args.command, result)
        if args.command == 'final':
            save(run / 'gate-result.json', result)
        print(json.dumps(result, ensure_ascii=True))
        return 2 if result['status'] == 'pending' else 1


if __name__ == '__main__':
    raise SystemExit(main())
