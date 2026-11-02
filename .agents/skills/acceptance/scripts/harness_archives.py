"""Preserve reviewed, unaffected historical harness executions using exact archived bytes.

This never substitutes archived product source, inputs, contracts or result evidence.
"""
from execution import file_current,require,target,stamp


def validate(record,workspace):
    cases=set(record['sequence'])
    for repair in record['repairs']:
        archive=(repair.get('resolution') or {}).get('harnessArchive')
        if not archive:
            continue
        require(repair['category']=='harness' and repair['status']=='resolved','Harness archive needs a resolved harness repair')
        previous=next((a['run'] for a in record['attempts'] if a['run']['id']==repair['attemptId']),None)
        require(previous is not None and archive['original']==previous['script'],'Archive must preserve the actual failed driver version')
        original,frozen=archive['original'],archive['archive']
        require(frozen['sha256']==original['sha256'] and file_current(frozen,workspace),'Harness archive bytes missing or changed')
        directory=target(previous['context']['path'],workspace).parent/'repair'
        require(directory in target(frozen['path'],workspace).parents,'Archive must stay with the actual failure repair evidence')
        preserved=set(archive['unaffectedCaseIds'])
        require(preserved<=cases and not preserved.intersection(repair['affectedCaseIds']),'Invalid unaffected harness case scope')
        require(any(f['path']==original['path'] and f['sha256']!=original['sha256'] for f in repair['resolution']['changedFiles']),
                'Harness archive requires an actual reviewed driver change')


def current(ref,attempt,record,workspace):
    if file_current(ref,workspace):
        return True
    # Only the actual entry script (also listed in files) has a historical-version exception.
    if ref!=attempt['run']['script']:
        return False
    case_id=record['sequence'][attempt['run']['visits'][0]['visitIndex']]
    for owner in record['repairs']:
        archive=(owner.get('resolution') or {}).get('harnessArchive')
        if not archive or owner['status']!='resolved' or archive['original']!=ref:
            continue
        if case_id not in archive['unaffectedCaseIds'] or stamp(attempt['authorizedAt'])>stamp(owner['openedAt']):
            continue
        if any(stamp(later['openedAt'])>stamp(owner['openedAt']) and case_id in later['affectedCaseIds'] for later in record['repairs']):
            continue
        approved=[f for repair in record['repairs'] if repair['status']=='resolved' and repair['category']=='harness'
                  and (repair.get('resolution') or {}).get('harnessArchive')
                  for f in repair['resolution']['changedFiles'] if f['path']==ref['path']]
        # An unreviewed subsequent edit cannot inherit an earlier preservation decision.
        if any(file_current(f,workspace) for f in approved) and file_current(archive['archive'],workspace):
            return True
    return False
