"""Project the fixed acceptance route into numbered rounds and query the next legal work item."""
import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path.cwd()
sys.path.insert(0, str(SKILL / 'scripts'))
import route
from execution import load_json, required_checks, file_current, digest
from case_contracts import filename
import artifact_copies
from schedule import entry_prefix
from input_snapshot import InputSnapshot

_BUILD_CACHE = None

BOUNDARIES = {'route-start':'路线起点','session-start':'会话起点','independent-fixture':'独立夹具入口','declared-initial-state':'已声明初态'}

LABELS = {'not_run':'待验收','queued':'等待前项','ready':'下一项','running':'进行中',
          'passed':'已通过','failed':'失败','blocked':'受阻','stale':'证据失效',
          'partial':'部分完成','recorded':'等待完成提交'}


def reference(path, workspace):
    return {'path':path.relative_to(workspace).as_posix(),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def _build(record_path, workspace):
    workspace, record_path = workspace.resolve(), record_path.resolve()
    record_path.relative_to(workspace)
    before = record_path.read_bytes()
    data = route.load_data(record_path, workspace)
    record, model, states = data['record'], data['model'], data['state']
    views_error = None
    try:
        route.check_views(data)
    except ValueError as error:
        views_error = str(error)
    cases = {c['id']:c for c in model['cases']}
    by_state = {s['id']:s for s in states['states']}
    sequence = record['sequence']
    initial = {s['id'] for s in states['states'] if s['isInitial']}
    sessions = {s['from']: s for s in record['sessions']}
    profiles = {p['id']: p for p in record['planning']['profiles']}
    starts = [i for i,cid in enumerate(sequence)
              if i == 0 or i in sessions or cases[cid]['kind'] != 'primary' or cases[cid]['given']['stateId'] in initial]
    occurrences, totals = Counter(), Counter(sequence)
    visits, rounds = [], []
    active, cursor = record['active'], data['cursor']
    unresolved = [r for r in record['repairs'] if r['status'] != 'resolved']
    for number, start in enumerate(starts, 1):
        session = route.session_for(record, start)
        profile = profiles[session['profileId']]
        boundary = []
        if start == 0: boundary.append('route-start')
        if start in sessions: boundary.append('session-start')
        if cases[sequence[start]]['kind'] != 'primary': boundary.append('independent-fixture')
        elif cases[sequence[start]]['given']['stateId'] in initial: boundary.append('declared-initial-state')
        end = starts[number] - 1 if number < len(starts) else len(sequence) - 1
        round_id = 'R' + str(number).zfill(2)
        for index in range(start, end + 1):
            case = cases[sequence[index]]
            occurrences[case['id']] += 1
            status = data['details'][index][0] if index in data['details'] else 'not_run'
            if active and active['visitIndex'] == index:
                status = 'recorded' if active['stage'] == 'recorded' else 'running'
            elif index == cursor and not active and not unresolved and data['implementationReady'] and not views_error:
                status = 'ready'
            elif status == 'not_run' and index > cursor:
                status = 'queued'
            prefix = entry_prefix(model, states, index)
            checks = [dict(aspect=aspect, checkIndex=check_index, **definition)
                      for aspect,check_index,definition in required_checks(case)
                      if definition['testType'] in record['testTypes']]
            visits.append(dict(order=index+1, visitIndex=index, roundId=round_id,
                               orderInRound=index-start+1, caseId=case['id'], title=case['title'],
                               occurrence=occurrences[case['id']], requiredOccurrences=totals[case['id']],
                               kind=case['kind'], status=status, caseAggregateStatus=case['execution']['status'],
                               given={**case['given'],'title':by_state.get(case['given']['stateId'],{}).get('title','独立检查准备')},
                               operation=case['operation'],
                               expected={**case['expected'],'title':by_state.get(case['expected']['stateId'],{}).get('title',case['expected']['conclusion'])},
                               checks=checks, mocks=case['mocks'], dataProfileId=case['dataProfileId'],
                               contractPath=(Path(record['contractsDirectory'])/filename(case['id'])).as_posix(),
                               contractHref='contracts/'+filename(case['id']),
                               sessionId=session['id'],profileId=profile['id'],contextKey=profile['contextKey'],
                               environments=sorted({c['environment'] for c in checks}),
                               predecessor=None if index==0 else {'visitIndex':index-1,'caseId':sequence[index-1]},
                               successor=None if index+1==len(sequence) else {'visitIndex':index+1,'caseId':sequence[index+1]},
                               normalEntry=('replay' if index in sessions and sessions[index]['entryReplay'] else
                                            'initial' if case['kind'] != 'primary' or case['given']['stateId'] in initial else 'handoff'),
                               coldResume={'caseIds':prefix,'operations':[cases[cid]['operation']['label'] for cid in prefix],
                                           'graphTransitionCount':len(prefix),'requiresContextVerification':True,
                                           'automaticReplayCapability':'not-verified'},
                               attemptIds=[a['run']['id'] for a in record['attempts'] if a['run']['visits'][0]['visitIndex']==index]))
        rows = visits[start:end+1]
        complete = all(v['status']=='passed' for v in rows)
        problem = next((s for s in ('failed','blocked','stale','recorded','running') if any(v['status']==s for v in rows)), None)
        round_status = ('passed' if complete else problem if problem else 'active' if start<=cursor<=end else
                        'partial' if any(v['status']=='passed' for v in rows) else 'queued')
        rounds.append(dict(id=round_id, number=number, fromVisitIndex=start,toVisitIndex=end,
                           fromOrder=start+1,toOrder=end+1,visitCount=end-start+1,
                           kind='primary' if cases[sequence[start]]['kind']=='primary' else 'independent',
                           title='主路线 '+str(number) if cases[sequence[start]]['kind']=='primary' else cases[sequence[start]]['title'],
                           firstCaseId=sequence[start],lastCaseId=sequence[end],
                           entryStateId=cases[sequence[start]]['given']['stateId'],
                           boundaryReasons=boundary,sessionId=session['id'],profileId=profile['id'],
                           contextKey=profile['contextKey'],resources=session['resources'],
                           plannedAdditionalEntryVisits=len(sessions[start]['entryReplay']) if start in sessions else 0,
                           servicePreparation='follow-session-profile' if start in sessions else 'reuse-compatible-context',status=round_status,
                           normalCompletion='全部访问通过并提交后进入下一轮；运行环境兼容时直接复用。',
                           pauseAfterVisitIndex=end,driverPauseCapability='not-verified'))
    item = visits[cursor] if cursor<len(visits) else None
    action, reason, can_begin = 'begin', '前项已关闭、视图一致，执行前仍须观察真实初态和环境。', True
    if active:
        action = 'resume-submit' if active['stage']=='recorded' else 'recover-active-visit'
        reason = '当前访问尚未关闭，须恢复当前观察或同一次提交，禁止重新 begin。'
        can_begin = False
        item = visits[active['visitIndex']]
    elif views_error:
        action, reason, can_begin = 'sync-projections', views_error, False
    elif not data['implementationReady']:
        action, reason, can_begin = 'refresh-implementation', '实现或静态检查证据已失效，需恢复当前版交接。', False
    elif unresolved:
        action, reason, can_begin = 'repair', '存在未关闭修复，先完成 repair-open/repair-close，再重验受影响访问。', False
    elif item is not None and any(
            not (closed and closed[-1]['exitCode'] == 0 and file_current(closed[-1]['log'], workspace))
            for session in record['sessions'] if session['to'] < route.session_for(record, item['visitIndex'])['from']
            for closed in [[r for r in record['sessionResults'] if r['sessionId'] == session['id']]]):
        action, reason, can_begin = 'close-previous-session', '前一执行会话尚未真实成功收尾，先核对退出结果和日志。', False
    elif item is None:
        action, reason, can_begin = 'close-sessions-and-finish', '全部访问完成，核对真实会话退出结果并运行 finish。', False
    if item and not can_begin and item['status'] == 'ready':
        item['status'] = 'not_run'
    next_work = dict(action=action,canBegin=can_begin,reason=reason,visit=item)
    if item:
        next_work['beginCommand'] = ['python','-B',(SKILL/'scripts/route.py').as_posix(),'begin',
                                    record_path.relative_to(workspace).as_posix(),'--workspace',workspace.as_posix(),
                                    '--index',str(item['visitIndex'])] if can_begin else None
        next_work['verification'] = '同次访问全部适用检查通过，submit 返回 recorded/synced/checked/canAdvance=true，再同步核对执行清单并实时查询 next 后继续。'
    if record_path.read_bytes()!=before:
        raise ValueError('Acceptance index changed while projecting; retry after its writer finishes')
    plan = dict(schemaVersion='1.0.0',title='验收执行计划',
                sourceRecord=reference(record_path,workspace),
                sourceCases=reference(data['casePath'],workspace),
                binding={'caseContract':record['caseContract'],'planContract':record['planContract'],
                         'scheduleContract':record['scheduleContract']},
                policy={'sequenceAuthority':'acceptance.json.sequence / test-cases.coverage.sequence',
                        'roundRule':'在路线起点、会话切换、声明初态与独立夹具入口切分连续逻辑轮次；不去重、不重排。',
                        'executionSessionCount':len(record['sessions']),
                        'servicesReusedAcrossRounds':'when-context-compatible',
                        'plannedAdditionalEntryVisits':record['planning']['objective']['additionalEntryVisits'],
                        'optimalityScope':'既定路线及已审查候选方案内按额外进入、准备单元、会话数的字典序最优；自然轮次不保证全局恢复成本最优。',
                        'roundsAreProcessSessions':False,'generatorExecutesProductActions':False,
                        'driverCapabilities':{'automaticRoundPause':'not-verified','automaticColdReplay':'not-verified'},'runtimeCapabilities':'须独立验证实际驱动；计划生成器不执行暂停或冷重放。',
                        'onFailure':'停止当前访问，保存失败并完成修复流程，不跳到后项。',
                        'onInterruption':'先核对已提交结果和当前状态；状态丢失时按所列候选入口核对上下文后重放，禁止从头重验全部。'},
                progress={'cursorVisitIndex':cursor,'nextOrder':item['order'] if item else None,
                          'acceptedVisits':sum(v['status']=='passed' for v in visits),
                          'active':active,'unresolvedRepairs':len(unresolved),
                          'implementationReady':data['implementationReady'],'viewsConsistent':views_error is None},
                next=next_work,rounds=rounds,visits=visits,
                totals={'rounds':len(rounds),'visits':len(visits),'uniqueCases':len(cases)})
    tool = Path(__file__).resolve()
    try: tool_name = tool.relative_to(workspace).as_posix()
    except ValueError: tool_name = tool.as_posix()
    base = ['python', '-B', tool_name]
    options = ['--workspace', workspace.as_posix(), '--record', record_path.relative_to(workspace).as_posix()]
    plan['commandHints'] = [' '.join(json.dumps(s,ensure_ascii=False) if ' ' in s else s for s in base+[command]+extra+options)
                            for command,extra in [('next',[]),('round',[rounds[0]['id']] if rounds else []),('list',[]),('sync',[]),('check',[])]]
    plan['snapshotId'] = digest(plan)
    return plan



def build(record_path, workspace):
    global _BUILD_CACHE
    key = (record_path.resolve(),workspace.resolve(),id(route.load_data),id(route.check_views))
    if _BUILD_CACHE is not None:
        previous_key,snapshot,plan = _BUILD_CACHE
        if key == previous_key and snapshot.current():
            return copy.deepcopy(plan)
    snapshot = InputSnapshot()
    with snapshot:
        plan = _build(record_path,workspace)
    if not snapshot.current():
        raise ValueError('Acceptance inputs changed while projecting; synchronize again')
    _BUILD_CACHE = (key,snapshot,copy.deepcopy(plan))
    return plan


def markdown(plan):
    item, nxt = plan['next']['visit'], plan['next']
    lines=['# 验收执行计划','',f"索引快照：{plan['snapshotId'][:12]}。实时查询以 `execution_plan.py next` 为准。",'']
    if item:
        lines += [f"**当前工作：{item['roundId']} · 第 {item['order']} 项 · {item['caseId']}**",'',
                  f"- 当前动作：`{nxt['action']}`；{'允许开始' if nxt['canBegin'] else '暂不允许开始新访问'}。",
                  '- 初态：'+item['given']['title'],'- 操作：'+item['operation']['label'],
                  '- 预期：'+item['expected']['title'],'- 本项检查：'+ '、'.join(item['environments']),
                  '- 下一项：'+(item['successor']['caseId'] if item['successor'] else '会话收尾与最终门禁'),
                  '- 放行条件：'+nxt['verification'],'- 门禁说明：'+nxt['reason'],'']
    lines += ['## 执行依据','',
              f"- {plan['totals']['uniqueCases']} 个用例，{plan['totals']['visits']} 次必要访问，{plan['totals']['rounds']} 个连续逻辑轮次。",
              f"- 复用现有 {plan['policy']['executionSessionCount']} 个执行会话；轮次之间不要求重启设备或服务。",
              '- 按下表和逐项清单执行，保留同一 Test Case 的必要重复；只有当前访问通过并同步后，才进入下一项。',
              f"- 轮次按会话边界、声明初态或独立夹具切分；计划内额外进入 {plan['policy']['plannedAdditionalEntryVisits']} 次。",
              '- 轮次是连续逻辑分组；按轮自动暂停和冷恢复必须由实际驱动实现并验证。本生成器只生成清单。',
              '- '+plan['policy']['optimalityScope'],
              '- 失败按修复流程停在当前项，禁止跳项；本计划不把静态检查或规划结果记为产品通过。','',
              '## 实时查询命令','',
              '```powershell',
              *plan['commandHints'],
              '```','',
              '- `next`：当前应处理的访问、所属轮次、门禁、初态、操作、预期和后继。',
              '- `round R01`：该轮全部用例的准确先后顺序。',
              f"- `list`：全部 {plan['totals']['visits']} 次访问，保留必要重复。",
              '- `sync`：从真实执行索引重建 JSON、Markdown 和 HTML 状态快照。',
              '- `check`：重新推导并核对三份清单；不同步时拒绝通过。','',
              '## 轮次总表','',
              '| 轮次 | 总序号（从 1 开始） | visitIndex | 访问数 | 起始用例 | 结束用例 | 划分依据 | 会话 |',
              '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in plan['rounds']:
        lines.append(f"| {r['id']} | {r['fromOrder']}–{r['toOrder']} | {r['fromVisitIndex']}–{r['toVisitIndex']} | {r['visitCount']} | {r['firstCaseId']} | {r['lastCaseId']} | {'、'.join(BOUNDARIES[b] for b in r['boundaryReasons'])} | {r['sessionId']} |")
    lines += ['', '## 逐项清单','',
              '[打开可筛选的完整清单](execution-plan.html) · [完整机器计划](execution-plan.json)','']
    for r in plan['rounds']:
        lines += [f"### {r['id']} · 第 {r['fromOrder']}–{r['toOrder']} 项",'',
                  '| 总序号 | Test Case | 初态 | 操作 | 预期终态 |',
                  '| --- | --- | --- | --- | --- |']
        for v in plan['visits'][r['fromVisitIndex']:r['toVisitIndex']+1]:
            clean=lambda s:str(s).replace('|','\\|').replace('\n',' ')
            lines.append('| '+' | '.join(map(clean,[v['order'],v['caseId'],v['given']['title'],v['operation']['label'],v['expected']['title']]))+' |')
        lines += ['']
    return '\n'.join(lines)


def html_document(plan):
    payload = json.dumps(plan, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return (SKILL / 'assets/execution-plan.template.html').read_text(encoding='utf-8').replace('{{EXECUTION_PLAN_JSON}}', payload)


def output_texts(plan):
    return {'execution-plan.json':json.dumps(plan,ensure_ascii=False,indent=2)+'\n',
            'execution-plan.md':markdown(plan),'execution-plan.html':html_document(plan)}


def validate_outputs(plan, directory, workspace):
    directory, workspace = directory.resolve(), workspace.resolve()
    record_path = workspace / plan['sourceRecord']['path']
    record = load_json(record_path)
    if record_path.parent != directory:
        raise ValueError('Execution plan must stay beside its acceptance record')
    artifact_copies.validate(record, workspace, [directory / name for name in output_texts(plan)])
    if not plan['progress']['viewsConsistent']:
        raise ValueError('Synchronize canonical contracts and views before publishing the execution plan')
    current = build(record_path, workspace)
    if current != plan:
        raise ValueError('Acceptance inputs changed while projecting; query and synchronize again')


def write_outputs(plan, directory, workspace=None):
    workspace = Path(workspace or DEFAULT_ROOT)
    validate_outputs(plan, directory, workspace)
    for name, text in output_texts(plan).items():
        target = directory / name
        temporary = target.with_suffix(target.suffix+'.tmp')
        temporary.write_bytes(text.encode('utf-8'))
        temporary.replace(target)
    check_outputs(plan, directory, workspace)


def check_outputs(plan, directory, workspace):
    validate_outputs(plan, directory, workspace)
    for name, text in output_texts(plan).items():
        file = directory / name
        if not file.is_file() or file.read_bytes() != text.encode('utf-8'):
            raise ValueError('Execution-plan view missing or stale: '+str(file))
    return {'status':'consistent','scope':'execution-plan-projections','snapshotId':plan['snapshotId']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['sync','check','next','round','list','status'])
    parser.add_argument('round_id',nargs='?')
    parser.add_argument('--workspace',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--record',type=Path)
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    workspace=args.workspace.resolve()
    record=args.record or workspace/'plan/acceptance/acceptance.json'
    if not record.is_absolute():record=workspace/record
    try:
        plan=build(record,workspace)
        if args.command=='round' and args.round_id not in {r['id'] for r in plan['rounds']}:
            raise ValueError('Unknown round: '+str(args.round_id))
        if args.command=='check':
            print(json.dumps(check_outputs(plan,record.parent,workspace),ensure_ascii=False,indent=2))
        elif args.command=='sync':
            write_outputs(plan,record.parent,workspace)
            print(json.dumps({'status':'synchronized','totals':plan['totals'],'next':{k:v for k,v in plan['next'].items() if k!='visit'},'nextCaseId':plan['next']['visit']['caseId'] if plan['next']['visit'] else None},ensure_ascii=False,indent=2))
        elif args.json:
            value=plan['next'] if args.command=='next' else plan['progress'] if args.command=='status' else [v for v in plan['visits'] if args.command=='list' or v['roundId']==args.round_id]
            print(json.dumps(value,ensure_ascii=False,indent=2))
        elif args.command=='next':
            nxt=plan['next'];v=nxt['visit']
            if v:
                print(f"{v['roundId']} / 第{v['order']}项 / visitIndex={v['visitIndex']} / {v['caseId']}")
                print('门禁：'+nxt['action']+'；'+('允许开始' if nxt['canBegin'] else '须先恢复/修复'))
                print('初态：'+v['given']['title']);print('操作：'+v['operation']['label']);print('预期：'+v['expected']['title'])
                print('检查：'+' + '.join(v['environments']));print('后继：'+(v['successor']['caseId'] if v['successor'] else '最终收尾'))
                print('说明：'+nxt['reason'])
            else:print(nxt['reason'])
        elif args.command=='status':
            print(json.dumps({'progress':plan['progress'],'rounds':[{k:r[k] for k in ('id','fromOrder','toOrder','status')} for r in plan['rounds']]},ensure_ascii=False,indent=2))
        else:
            if args.command=='round' and args.round_id not in {r['id'] for r in plan['rounds']}:raise ValueError('Unknown round: '+str(args.round_id))
            for v in plan['visits']:
                if args.command=='list' or v['roundId']==args.round_id:
                    print(f"{v['order']:03d} | {v['roundId']} | {v['caseId']} | {v['given']['title']} → {v['operation']['label']} → {v['expected']['title']} | {LABELS.get(v['status'],v['status'])}")
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'blocked','error':str(error)},ensure_ascii=False));return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
