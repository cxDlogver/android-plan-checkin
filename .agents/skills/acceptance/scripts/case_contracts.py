"""One derived JSON contract per Test Case; frozen definitions and append-only actual attempts."""
import copy
import re
from execution import digest, file_current, load_json, target


def definition(case, model):
    value = copy.deepcopy(case)
    value.pop('execution', None)
    value['dataProfile'] = copy.deepcopy(next(p for p in model['dataProfiles'] if p['id'] == case['dataProfileId']))
    return value


def definition_hash(case, model):
    return digest(definition(case, model))


def filename(case_id):
    return (case_id if re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,120}', case_id) else digest(case_id)) + '.json'


def contract(data, case):
    record = data['record']
    current_hash = definition_hash(case, data['model'])
    sequence = data['model']['coverage']['sequence']
    history = []
    for attempt in record['attempts']:
        run = attempt['run']
        visit = run['visits'][0]
        index = visit['visitIndex']
        if sequence[index] != case['id']:
            continue
        checks = []
        for result in visit['checks']:
            key = 'case:' + case['id'] + ':' + result['aspect'] + ':' + str(result['checkIndex']) + ':' + str(index)
            comparisons = []
            for ref in result['evidence']:
                if ref['form'] == 'assertion-report' and file_current(ref, data['workspace']):
                    rows = load_json(target(ref['path'], data['workspace'])).get('assertions', [])
                    comparisons.extend(dict(expected=copy.deepcopy(r['expected']), actual=copy.deepcopy(r['actual']),
                                            verdict=r['verdict']) for r in rows if r.get('target') == key)
            checks.append(dict(aspect=result['aspect'], checkIndex=result['checkIndex'], status=result['status'],
                               observation=result['actual'], comparisons=comparisons, evidence=copy.deepcopy(result['evidence'])))
        history.append(dict(attemptId=run['id'], visitIndex=index, definitionHash=attempt['definitionHash'],
                            definition=copy.deepcopy(record['definitions'][attempt['definitionHash']]),
                            givenObserved=visit['givenObserved'], operationObserved=visit['operationObserved'],
                            targetObserved=visit['targetObserved'], outcome=visit['outcome'],
                            startedAt=run['startedAt'], finishedAt=run['finishedAt'],
                            definitionCurrent=attempt['definitionHash'] == current_hash, checks=checks,
                            blockage=copy.deepcopy(visit.get('blockage'))))
    return dict(schemaVersion='1.0.0', caseId=case['id'], title=case['title'],
                source=dict(path=record['testCasesPath'], definitionHash=current_hash),
                definition=definition(case, data['model']),
                stateGraph=copy.deepcopy(data['model']['stateGraph']),
                givenState=copy.deepcopy(next((s for s in data['state']['states'] if s['id'] == case['given']['stateId']), None)),
                expectedState=copy.deepcopy(next((s for s in data['state']['states'] if s['id'] == case['expected']['stateId']), None)),
                requiredVisits=[i for i, cid in enumerate(sequence) if cid == case['id']],
                execution=copy.deepcopy(case['execution']), attempts=history,
                repairs=[copy.deepcopy(r) for r in record['repairs'] if case['id'] in r['affectedCaseIds']])


def projections(data):
    directory = target(data['record']['contractsDirectory'], data['workspace'])
    return [(directory / filename(case['id']), contract(data, case)) for case in data['model']['cases']]
