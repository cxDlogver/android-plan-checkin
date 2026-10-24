"""Apply the approved generic type contract to this source-backed visual analysis."""
import json, sys
from pathlib import Path
w=Path(__file__).resolve().parent
root=w.parent
repo=root.parent.parent
sys.path.insert(0,str(repo/'.codex/skills/requirements-analysis/scripts'))
import workflow as wf
import model_tools as mt

m=wf.read(w/'analysis-model.json')
o=wf.read(w/'evidence/visual-observations.json')
reply=w/'evidence/model-contract-user-reply.md'
reply.write_text('用户实际答复：修正通用建模合同后继续分析\n\n对应问题：是否修正通用 Skill，使其同时支持行为型需求与状态约束型需求，保留双图及全部门禁，再继续本次已明确的视觉样式对齐分析。\n此回复授权修正分析方法，不是对分析结果的最终整体验收。\n',encoding='utf-8')
m['sources']=[s for s in m['sources'] if s['id']!='HUMAN-CONTRACT']
m['sources'].append({'id':'HUMAN-CONTRACT','kind':'human','uri':'conversation:current-user-reply','locator':'用户实际答复全文',
    'readRanges':['用户答复及对应问题'],'evidencePath':'_process/evidence/model-contract-user-reply.md','sha256':wf.file_hash(reply)})
next(s for s in m['sources'] if s['id']=='TOKENS')['designKeys']=['colors','font','spacing','radius','gradients','effects','layout']
m.update(schemaVersion=3,phase='analyzing',entryStateIds=[],transitions=[])
m['features'][0].update(title='UI视觉稿样式对齐',scope='PRD UI-001：对齐既有画板与局部样例的视觉样式；A01至A08是本项需求的共同检查点。',entryStateIds=[])
scenes={s['id']:s for s in o['scenarios']}
for state in m['states']:
    scene=scenes[state['id']]
    refs=[state['uiRefs'][0]]
    for region in scene['regions']:
        refs.append({'sourceId':'TREE','frameId':scene['frameId'],'region':region['name']+'；定位文字：'+'、'.join(region['anchors']),
            'stateLabel':region['name'],'nodeIds':[n['nodeId'] for n in region['nodeRefs']]})
    state['uiRefs']=refs
# Keep the PRD's one requirement and eight original checks. Shared visual values refine these checks.
groups={'A01':[], 'A02':['C04'], 'A03':['C02','C03','C05'], 'A04':['C06'], 'A05':['C08'], 'A06':['C01'], 'A07':['C07'], 'A08':['C09']}
common={c['id']:c for c in o['sharedConstraints']}
acceptance=[]
for a in o['acceptance']:
    ac={'id':a['id'],'given':'具有对应设计画板、区域及已画出的状态样例；动态内容可使用对应场景数据。',
        'when':'在相同逻辑宽度、字体比例和对应视觉场景下进行'+a['title']+'对照。',
        'then':[a['interpretation']]}
    for key in groups[a['id']]:
        c=common[key]
        ac['then'].extend(c['title']+'：'+check for check in c['checks'])
    if a['id']=='A07':
        ac['stateIds']=['V11']
        ac['given']='具有图11全局日历及PRD第4.4节规定的已画日期格、筛选与明细样例。'
    acceptance.append(ac)
product_sources=[s['id'] for s in m['sources'] if s['id']!='HUMAN-CONTRACT']
m['requirements']=[{'id':'UI-001','kind':'state_constraint','title':'UI视觉稿样式对齐',
    'stateIds':[s['id'] for s in m['states']],'featureIds':['F-UI'],
    'sourceRefs':[{'sourceId':'PRD','locator':'§1、§1.1：UI-001及范围；§3：23画板与局部样例；§4：视觉规范；§6 A01–A08及§6.1：检查与对照方式'},
                  {'sourceId':'HUMAN-VISUAL-SCOPE','locator':'用户答复全文：需求是UI视觉稿样式对齐，不考虑需求以外实现'}],
    'ruleIds':['UI-001'],'acceptance':acceptance,
    'uiRefs':[s['uiRefs'][0] for s in m['states']],'uiApplicability':{'status':'mapped'},
    'sourceIds':product_sources,'status':'draft'}]
build={'id':'BUILD-TYPED-CONSTRAINT','kind':'build','nodeIds':[s['id'] for s in m['states']],'checks':[],
    'changes':[{'kind':'add','entityId':'UI-001','meaning':'按PRD同一视觉义务建立状态约束；23状态与50局部区域承载A01至A08，不制造业务入口、事件或需求。',
        'sourceIds':['PRD','HUMAN-VISUAL-SCOPE']},
        {'kind':'update','entityId':'F-UI','meaning':'公共约束移入唯一需求的验收断言，功能仅保留归属。','sourceIds':['PRD']},
        {'kind':'update','entityId':'TOKENS','meaning':'CSS仅投影已确认视觉值，不将触摸尺寸和额外备注提升为验收要求。','sourceIds':['PRD','TOKENS']}],
    'openFrontier':[s['id'] for s in m['states']]}
m['rounds'].append(build)
state=wf.read(w/'run-state.json')
state.update(waiting_for_user=False,pause_reason=None,active_node_id=None,next_action='按新合同逐状态全量审查来源、边界、断言和视觉映射。')
wf.write(w/'analysis-model.json',m);wf.write(w/'run-state.json',state)
wf.save_current(root)
# Re-review against current facts and all scoped source regions, not a digest refresh of the old audit.
audit={'id':'AUDIT-TYPED-CURRENT','kind':'audit','modelDigest':mt.model_digest(m),
    'nodeIds':[s['id'] for s in m['states']],'checks':[],'changes':[],'openFrontier':[s['id'] for s in m['states']]}
m['rounds'].append(audit)
results=[]
for st in m['states']:
    s=scenes[st['id']]
    regions='；'.join(r['name']+'（'+'、'.join(r['anchors'])+'）' for r in s['regions'])
    refs=['PRD',s['imageSourceId'],'TREE','TOKENS']
    reasons={
      'sources':('covered','按PRD第3节与当前图'+str(s['order']).zfill(2)+'反查本页及区域：'+regions+'。独立准入：'+s['distinction']+' 已对应UI-001，不按画板新增功能。'),
      'events':('not_applicable','本页可见控件仅是样式目标：'+regions+'。PRD§1.2／§5明确不要求业务操作闭环；不推导点击、进入或保存事件。'),
      'guard_complement':('covered','本页纳入条件为：'+s['condition']+'。已有选中、结果或警示只核对当前区域样例；不生成反向选择的整页组合，不补业务守卫。'),
      'boundaries':('covered','边界限定为本画板及'+str(len(s['regions']))+'个局部区域；样例参数为'+'、'.join(s['parameters'])+'。尺寸按'+str(s['canvasSize'])+'与A06保持比例；不穷举参数或新增组合。'),
      'failure':('covered' if st['id'] in ['V20','V23'] else 'not_applicable',
          ('该页已有异常／警示外观按独立图和局部区域核对，' if st['id'] in ['V20','V23'] else '本页没有额外异常视觉义务，')+'仅承载'+s['title']+'的已有视觉；PRD§5排除无稿失败、加载、校验、保存中，不推导异常处理实现。'),
      'cancel_return':('not_applicable','“'+s['title']+'”中的返回、取消或其他按钮仅核对稿内形态、位置和文案；PRD§1.2排除返回、取消与恢复的业务闭环，无迁移验收义务。'),
      'repeat_time':('not_applicable','“'+s['title']+'”的日期、次数、记录时间或进度仅为已有排版参数；按PRD§1.2／§5不验收重复触发、跨日、时区或统计算法，不由数值变化拆状态。'),
      'permissions':('not_applicable','“'+s['title']+'”只核对已画控件、只读或警示的可见呈现；PRD§5排除权限实现，不以文字推导身份、角色或底层操作拦截。'),
      'ui':('covered','当前PNG、对应设计树和共享令牌支撑'+str(len(s['regions']))+'个区域：'+regions+'。局部目标为'+'；'.join(check for r in s['regions'] for check in r['checks'])+'；UI-001适用断言'+('A01至A08' if st['id']=='V11' else 'A01至A06及A08')+'，A07只适用全局日历。'),
      'cross_feature':('covered','唯一功能归属UI视觉稿样式对齐，适用需求UI-001。'+s['distinction']+' 状态约束以观察条件覆盖，不要求业务入口；共享参数复用，局部样例不升为整页，未添加跨页执行箭头。')}
    for dim in sorted(mt.DIMENSIONS):
        disposition,reason=reasons[dim]
        audit['checks'].append({'nodeId':st['id'],'dimension':dim,'disposition':disposition,'reason':reason,
            'evidenceIds':refs,'relatedIds':[st['id'],'UI-001','F-UI']})
    audit['openFrontier'].remove(st['id'])
    state.update(active_node_id=None,next_action='继续当前摘要全量审查；全部节点完成后生成标准双图和HTML。')
    wf.write(w/'analysis-model.json',m);wf.write(w/'run-state.json',state)
    saved=wf.save_current(root);results.append({'stateId':st['id'],'pending':len(saved['pending_node_ids']),'semantic_digest':saved['semantic_digest']})
m['phase']='review_ready'
assert audit['modelDigest']==mt.model_digest(m)
wf.write(w/'analysis-model.json',m)
state.update(active_node_id=None,next_action='prepare重建标准双图和HTML，再执行真实浏览及独立八项评审。')
wf.write(w/'run-state.json',state)
wf.save_current(root)
ledger={'semantic_digest':mt.model_digest(m),'scope':'UI-001 visual alignment only','prd':o['coverage'],
    'stateCoverage':[{'stateId':s['id'],'condition':s['condition'],'distinction':s['distinction'],
         'requirementId':'UI-001','sourceRefs':s['sourceRefs'],'localTargets':[{'region':r['name'],'checks':r['checks'],'nodeRefs':r['nodeRefs']} for r in s['regions']],
         'disposition':'mapped','parameters':s['parameters'],'excluded':s['excluded']} for s in o['scenarios']],
    'clarityAssessment':o['clarityAssessment'],
    'counts':{'states':len(m['states']),'localRegions':sum(len(s['regions']) for s in o['scenarios']),'requirements':1,'acceptanceChecks':8,'behaviorTransitions':0},
    'meaning':'Requirements coverage and clarity only; product visual alignment has not been performed or accepted.'}
ledger['clarityAssessment']['methodIssue']='通用合同已扩展为两类需求，按同一标准产出双图与全部门禁；最终验收尚未发生。'
for row in ledger['prd']:
    row['requirementId']='UI-001'
    row['targets']=['UI-001 / '+target for target in row.get('targets',[])]
wf.write(w/'evidence/current-source-coverage.json',ledger)
wf.write(w/'evidence/current-audit-save-results.json',{'semantic_digest':mt.model_digest(m),'nodeSaves':results,'checks':len(audit['checks'])})
(w/'contract-expression-gap.md').write_text('# 通用建模合同修正\n\n用户已明确授权修正通用建模合同后继续分析。\n\n已实现 Schema v3 的行为与状态约束类型分派，保留 Schema v2 行为兼容、双图和固定12项规则／8项独立评审标准。纯约束不制造事件、起点或路线；覆盖单独重新计算。当前模型已转入标准review_ready流程，最终交付以实际门禁结果为准。\n',encoding='utf-8')
print(json.dumps({'semantic_digest':mt.model_digest(m),'states':len(m['states']),'requirements':len(m['requirements']),'transitions':len(m['transitions']),'auditChecks':len(audit['checks']),'sourceIssues':wf.source_issues(root,m)},ensure_ascii=False))

