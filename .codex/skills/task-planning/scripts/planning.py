"""Current-file task planning, deterministic exports and fail-closed phase checks."""
import argparse, base64, copy, hashlib, json, sys
from pathlib import Path
from routes import replay
from graph_mapping import project_graph, inherit_routes, read_review

ROLES={'analysisModel','stateGraph','requirements','requirementGraph','prd','uiSpec','tokens','pageMap','requirementsReview'}
OUTPUTS={'test-plan.json':'后续结构化消费','test-cases.md':'测试步骤及预期','implementation-plan.md':'开发计划','review.html':'人工图形审查','gate-result.json':'当前门禁'}
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(obj):return sha(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(obj,ensure_ascii=False,indent=2)+'\n' if not isinstance(obj,str) else obj
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(text,encoding='utf-8');tmp.replace(p)
def work(root):return Path(root)/'_process/planning.json'
def generator_digest():
    root=Path(__file__).resolve().parent.parent
    paths=[root/'SKILL.md']
    for folder in ('scripts','assets','references'):
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('test_'))
    return digest([(p.relative_to(root).as_posix(),sha(p.read_bytes())) for p in sorted(paths)])
def plan_digest(cfg):
    c=copy.deepcopy(cfg)
    for k in ('phase','results','developmentEvidence'):c.pop(k,None)
    for t in c.get('tasks',[]):t.pop('status',None)
    return digest({'work':c,'generatorDigest':generator_digest()})
def code_digest(cfg):
    root=Path(cfg['repository']['root']);paths=set()
    for part in cfg['repository'].get('codeRoots',['src','app','tests','package.json']):
        p=root/part
        if p.is_dir():paths.update(x for x in p.rglob('*') if x.is_file() and not any(a in ('__pycache__','node_modules','.git') for a in x.parts))
        elif p.is_file():paths.add(p)
    return digest([(p.relative_to(root).as_posix(),sha(p.read_bytes())) for p in sorted(paths)])
def load_inputs(cfg):
    by={r['role']:r for r in cfg['inputs']}
    missing=ROLES-set(by)
    if missing:raise ValueError('missing inputs: '+','.join(sorted(missing)))
    if len(by)!=len(cfg['inputs']):raise ValueError('duplicate input roles')
    for r in by.values():
        if sha(Path(r['path']).read_bytes())!=r['sha256']:raise ValueError('stale input: '+r['role'])
    for r in cfg.get('uiAssets',[]):
        if sha(Path(r['path']).read_bytes())!=r['sha256']:raise ValueError('stale UI asset: '+r['path'])
    previews={str((Path(by['pageMap']['path']).parent/r['preview']).resolve()) for r in read(by['pageMap']['path'])['screens']}
    if {str(Path(r['path']).resolve()) for r in cfg.get('uiAssets',[])}!=previews:raise ValueError('UI asset hashes must cover exactly referenced previews')
    m=read(by['analysisModel']['path']);sg=read(by['stateGraph']['path']);req=read(by['requirements']['path']);rg=read(by['requirementGraph']['path'])
    if sg['nodes']!=m['states'] or sg['edges']!=m['transitions']:raise ValueError('state graph differs from model')
    exported={r['id']:r for r in req['requirements']}
    if len(exported)!=len(req['requirements']) or set(exported)!={r['id'] for r in m['requirements']}:raise ValueError('atomic requirement identities differ')
    for r in m['requirements']:
        if any(exported[r['id']].get(k)!=v for k,v in r.items()):raise ValueError('atomic requirements differ from model')
    rs={r['id']:r for r in m['requirements']};ts={t['id']:t for t in m['transitions']}
    stateids={s['id'] for s in m['states']}
    if len(stateids)!=len(m['states']) or not m.get('entryStateIds') or not set(m['entryStateIds'])<=stateids:raise ValueError('invalid state identity or real entries')
    if any(t['from'] not in stateids or t['to'] not in stateids for t in ts.values()):raise ValueError('dangling state edge')
    if len(rs)!=len(m['requirements']) or len(ts)!=len(m['transitions']):raise ValueError('duplicate input ids')
    if len(rs)!=len(ts) or {r['transitionId'] for r in rs.values()}!=set(ts):raise ValueError('requirements and transitions must be bijective')
    for r in rs.values():
        if ts[r['transitionId']]['requirementId']!=r['id']:raise ValueError('mismatched requirement owner')
    if len(rg['nodes'])!=len(rs) or {n['id'] for n in rg['nodes']}!=set(rs):raise ValueError('requirement graph nodes differ')
    for e in rg['edges']:
        if e['from'] not in rs or e['to'] not in rs:raise ValueError('unknown requirement edge')
        if ts[rs[e['from']]['transitionId']]['to']!=ts[rs[e['to']]['transitionId']]['from']:raise ValueError('invalid requirement continuation')
    read_review(by['requirementsReview']['path'],m,rg)
    if cfg.get('regressionPolicy',{}).get('mode') == 'deferred' and cfg.get('regressions'):
        raise ValueError('regressions are deferred by scope')
    return by,m,rg

def make_cases(cfg,m):
    states={s['id']:s for s in m['states']};ts={t['id']:t for t in m['transitions']};out=[];shared={}
    classified={text:rule for rule in cfg.get('sharedAssertions',[]) for text in rule['matches']}
    for r in m['requirements']:
        t=ts[r['transitionId']];assertions=[];gids=[]
        for a in r['acceptance']:
            for text in a['then']:
                if text in classified:
                    rule=classified[text];gid=rule['id'];shared[gid]={'id':gid,'text':rule['text'],'sourceRefs':r['sourceIds']};gids.append(gid);continue
                assertions.append({'id':'functional-'+str(len(assertions)+1),'kind':'functional','text':text,'sourceRefs':r['sourceIds'],'applicability':'supported'})
        refs=r.get('uiRefs',[])
        assertions.append({'id':'visual-reference','kind':'visual','text':'按适用画板的对应区域与 UI 文字规范核对当前状态；示例数据不作为连续流程事实，未规定装饰不新增。' if refs else '本需求没有独立视觉定义，不增加稿外样式。','sourceRefs':list(dict.fromkeys(u['sourceId'] for u in refs)),'applicability':'supported' if refs else 'not_specified'})
        c={'id':'TC-'+r['id'],'kind':'primary','requirementId':r['id'],'transitionId':t['id'],'title':r['title'],
           'featureIds':t['featureIds'],'from':t['from'],'to':t['to'],
           'setup':[a['given'] for a in r['acceptance']],'steps':[t['event']],
           'guard':t['guard'],'expectedState':states[t['to']]['title'],'assertions':assertions,
           'uiRefs':refs,'globalConstraintIds':list(dict.fromkeys(gids)),
           'instances':copy.deepcopy(cfg.get('defaultInstances',[{'id':'baseline','label':'标准场景'}])),
           'readiness':'blocked','readinessReason':'逐段夹具与自然语言守卫待具体化；上游草案不自动转为正式验收基线。'}
        override=cfg.get('overrides',{}).get(r['id'],{})
        allowed={'setup','steps','instances','readiness','readinessReason','additionalAssertions','regressionPurpose'}
        if set(override)-allowed:raise ValueError('unsupported case override')
        extra=copy.deepcopy(override.get('additionalAssertions',[]))
        c.update({k:copy.deepcopy(v) for k,v in override.items() if k!='additionalAssertions'});c['assertions'].extend(extra);out.append(c)
    for r in cfg.get('regressions',[]):
        c=copy.deepcopy(r);c['kind']='regression';c.setdefault('instances',[{'id':'host','label':'宿主自动化保护'}]);c.setdefault('uiRefs',[]);c.setdefault('globalConstraintIds',[]);out.append(c)
    for c in out:
        c['result']=copy.deepcopy(cfg.get('results',{}).get(c['id'],{'status':'pending','actual':None,'evidence':[]}))
        c['evidenceRequirements']=['记录环境、代码摘要、准备数据和执行顺序','逐条功能断言给实际结果与证据位置','适用视觉断言给同状态截图、设计对应区域与测量说明']
    return out,list(shared.values())

def css_tokens(t):
    lines=['/* 设计参考值；Native 尺寸按 dp/sp 映射，非 CSS 实现指令。 */',':root {']
    for k,v in t.get('colors',{}).items():lines.append('  --color-'+k+': '+v+';')
    for k,v in t.get('radius',{}).items():lines.append(f'  --radius-{k}: {v}px;')
    for k in ('body','caption','title','section'):
        if k in t.get('font',{}):lines.append(f'  --font-{k}: {t["font"][k]}px;')
    for k,v in t.get('gradients',{}).items():
        stops=', '.join(s['color']+' '+str(round(s['position']*100,3))+'%' for s in v['colors'])
        lines.append(f'  --gradient-{k}: linear-gradient({v["rotation"]}deg, {stops});')
    lines+=['}']
    if 'pageInset' in t.get('layout',{}):lines.append(f'.reference-page {{ padding-inline: {t["layout"]["pageInset"]}px; }}')
    if 'minimumTouchTarget' in t:lines.append(f'.reference-control {{ min-width: {t["minimumTouchTarget"]}px; min-height: {t["minimumTouchTarget"]}px; }}')
    for k,effects in t.get('effects',{}).items():
        shadows=[]
        for e in effects:
            off=e.get('offset',{})
            if all(key in off for key in ('x','y')) and 'blur' in e and 'color' in e:shadows.append(('inset ' if e.get('shadowType')=='inner' else '')+f'{off["x"]}px {off["y"]}px {e["blur"]}px '+e['color'])
            else:lines.append('/* '+k+' 的阴影参数未完整提供，未生成推测值。 */')
        if shadows:lines.append('.reference-'+k+' { box-shadow: '+', '.join(shadows)+'; }')
    if t.get('font'):
        f=t['font'];body=[]
        if 'preferredFamily' in f:body.append(f'font-family: "{f["preferredFamily"]}"')
        if 'body' in f:body.append(f'font-size: {f["body"]}px')
        if 'lineHeightRatio' in f:body.append(f'line-height: {f["lineHeightRatio"]}')
        if body:lines.append('.reference-body { '+'; '.join(body)+'; }')
        if 'titleWeight' in f:lines.append(f'.reference-title {{ font-weight: {f["titleWeight"]}; }}')
    if t.get('layout'):
        layout=t['layout'];card=[]
        if 'cardPadding' in layout:card.append(f'padding: {layout["cardPadding"]}px')
        if 'sectionGap' in layout:card.append(f'gap: {layout["sectionGap"]}px')
        if card:lines.append('.reference-card { '+'; '.join(card)+'; }')
    return '\n'.join(lines)

def assemble(cfg,by,m,rg):
    cases,shared=make_cases(cfg,m);routes=inherit_routes(m,rg);ts={t['id']:t for t in m['transitions']};cs={c.get('transitionId'):c['id'] for c in cases if c['kind']=='primary'}
    edges=[]
    for route in routes['routes']:
        route['routeDigest']=digest({'entry':route['entryStateId'],'steps':route['steps']})
        preparation=cfg.get('routePreparations',{}).get(route['id'])
        if preparation and preparation.get('routeDigest')==route['routeDigest']:
            route['fixture']=preparation
            route['preparation']='；'.join(preparation.get('setup',[]))
            if all(preparation.get(k) for k in ('setup','controls','restore','sourceRefs','guardReview')):
                route['fixtureStatus']='ready'
        for i,s in enumerate(route['steps']):
            s['caseId']=cs[s['transitionId']]

    # Harness cases cannot be smuggled into the product transition graph.
    harness=[{'id':'harness-'+c['id'],'kind':'harness','title':'测试准备：'+c['title'],'caseIds':[c['id']],'setup':c['setup'],'steps':c['steps']} for c in cases if c['kind']=='regression']
    media={};pm=read(by['pageMap']['path'])
    for row in pm['screens']:
        p=Path(by['pageMap']['path']).parent/row['preview']
        media[row['frameId']]={'title':row['title'],'caption':row.get('designCaption',''),'data':'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode(),'sha256':sha(p.read_bytes())}
    return {'planningDigest':plan_digest(cfg),'codeDigest':code_digest(cfg),'phase':cfg['phase'],'scope':cfg['scope'],
            'inputs':cfg['inputs'],'sources':m['sources'],'repository':cfg['repository'],'issues':cfg['issues'],
            'acceptanceMatrix':cfg.get('acceptanceMatrix'),
            'stateGraph':{'entryStateIds':m['entryStateIds'],'nodes':m['states'],'edges':m['transitions']},
            'requirementGraph':copy.deepcopy(rg),'testGraph':project_graph(m,rg,cases),
            'regressionPolicy':cfg.get('regressionPolicy',{'mode':'included'}),
            'cases':cases,'sharedConstraints':shared,'routes':routes,'harnessRoutes':harness,'tasks':cfg['tasks'],
            'upstreamTraversal':{'reduction':rg.get('reduction'),'traversalSummary':{k:v for k,v in rg.get('traversal',{}).items() if k not in ('routes','steps','segments')}},
            'css':css_tokens(read(by['tokens']['path'])),'media':media}

def evidence_ok(root,e):
    try:
        p=(Path(root)/e['path']).resolve();p.relative_to(Path(root).resolve())
        return p.is_file() and sha(p.read_bytes())==e['sha256'] and bool(e.get('locator'))
    except (KeyError,ValueError,TypeError):return False

def validate_result(root,p,c,result):
    errors=[]
    if result.get('planningDigest')!=p['planningDigest'] or result.get('codeDigest')!=p['codeDigest']:errors.append('stale result digest')
    env=result.get('environment',{})
    if not all(env.get(k) for k in ('platform','build','fixture','executedAt')):errors.append('missing execution environment')
    wanted={(i['id'],a['id']) for i in c['instances'] for a in c['assertions'] if a['applicability']=='supported'}
    observations=result.get('observations',[]);actual={(o.get('instanceId'),o.get('assertionId')) for o in observations}
    if not actual<=wanted or len(actual)!=len(observations):errors.append('unknown or duplicate observation')
    for o in observations:
        if o.get('verdict') not in ('passed','failed') or not o.get('actual'):errors.append('invalid actual result')
        if not o.get('evidence') or not all(evidence_ok(root,e) for e in o['evidence']):errors.append('missing or stale evidence')
    status='failed' if any(o.get('verdict')=='failed' for o in observations) else 'passed' if actual==wanted and wanted else 'pending'
    if result.get('status')!=status:errors.append('invalid aggregate result status')
    return errors

def check_model(root,cfg,p,m):
    errors=[];issues=[];cases=p['cases'];ids=[c['id'] for c in cases]
    if len(ids)!=len(set(ids)):errors.append('duplicate case id')
    if cfg.get('regressionPolicy',{}).get('mode')=='deferred' and any(t.get('regressionIds') for t in cfg['tasks']):errors.append('task references regression while deferred')
    taskids={t['id'] for t in cfg['tasks']}
    if len(taskids)!=len(cfg['tasks']):errors.append('duplicate task id')
    requirements={r['id'] for r in m['requirements']}
    if not cfg['scope'].get('initialConfirmation',{}).get('humanReply'):errors.append('initial human clarification missing')
    if cfg['routePolicy'].get('resetAllowed') and not cfg['routePolicy'].get('resetReason'):errors.append('reset policy requires reason')
    mapped=set()
    for t in cfg['tasks']:
        if not t.get('approach') or not t.get('doneWhen') or not t.get('codePaths'):errors.append('incomplete task '+t['id'])
        if not set(t['dependsOn'])<=taskids:errors.append('unknown task dependency')
        if not set(t['requirementIds'])<=requirements:errors.append('unknown task requirement')
        mapped.update(t['requirementIds'])
        for c in t['checks']:
            if c['kind'] not in ('static','unit'):errors.append('product/integration acceptance in development')
        if not t['checks'] and not t.get('checksNotNeededReason'):errors.append('missing development checks or explicit rationale')
    if mapped!=requirements:errors.append('unmapped requirement in implementation tasks')
    pending={t['id']:set(t['dependsOn']) for t in cfg['tasks']}
    while pending:
        ready={k for k,v in pending.items() if not v}
        if not ready:errors.append('task dependency cycle');break
        pending={k:v-ready for k,v in pending.items() if k not in ready}
    for c in cases:
        if not c.get('setup') or not c.get('steps') or not c.get('expectedState'):errors.append('incomplete test '+c['id'])
        if not any(a['kind']=='functional' and a['applicability']=='supported' for a in c['assertions']):errors.append('no supported functional assertion')
        if any(not a.get('id') for a in c['assertions']) or any(not i.get('id') for i in c['instances']):errors.append('empty assertion or instance id')
        if c['readiness'] not in ('ready','blocked') or c['result']['status'] not in ('pending','failed','passed'):errors.append('invalid case status')
        if len({a['id'] for a in c['assertions']})!=len(c['assertions']):errors.append('duplicate assertion id')
        if not c.get('instances') or len({i['id'] for i in c['instances']})!=len(c['instances']):errors.append('missing or duplicate instance')
        if any(not a.get('text') or a.get('kind') not in ('functional','visual') or a.get('applicability') not in ('supported','not_specified','not_applicable') or a['applicability']=='supported' and not a.get('sourceRefs') for a in c['assertions']):errors.append('invalid assertion/source')
        if c['kind']=='regression' and not all(c.get('impact',{}).get(k) for k in ('changedPaths','affectedPaths','existingContract','risk','sourceRefs','whyNotCovered')):errors.append('unjustified regression')
        if c['readiness']!='ready':issues.append('测试数据/步骤待具体化：'+c['title'])
        if c['result']['status']!='pending':
            if cfg['phase']!='acceptance':errors.append('result outside acceptance phase')
            errors.extend(validate_result(root,p,c,c['result']))
    source_graph=read(next(r['path'] for r in cfg['inputs'] if r['role']=='requirementGraph'))
    if p.get('requirementGraph')!=source_graph:errors.append('requirement graph source differs')
    if p['testGraph']!=project_graph(m,source_graph,cases):errors.append('test graph must exactly map requirement nodes, edges and entries')
    inherited=inherit_routes(m,source_graph)
    for r,source in zip(p['routes']['routes'],inherited['routes']):
        if r['steps']!=source['steps'] or r['entryStateId']!=source['entryStateId'] or r['contextCheck']!=source['contextCheck']:errors.append('inherited route was changed')
    if len(p['routes']['routes'])!=len(inherited['routes']):errors.append('inherited route count differs')
    if not inherited['executable']:issues.append('需求覆盖路线的执行条件未通过；原样保留并阻止作为正式验收顺序')
    cs={c['id']:c for c in cases}
    for rule in cfg.get('sharedAssertions',[]):
        bindings=rule.get('coveredBy',[])
        if not bindings:issues.append('共享约束尚未绑定验收断言：'+rule['text'])
        for b in bindings:
            if b.get('caseId') not in cs or b.get('assertionId') not in {a['id'] for a in cs.get(b.get('caseId'),{}).get('assertions',[])}:errors.append('invalid shared constraint binding')
    matrix=cfg.get('acceptanceMatrix',{})
    bindings=matrix.get('bindings',[])
    for env in matrix.get('environments',[]):
        matches=[b for b in bindings if b.get('environment')==env]
        if not matches:issues.append('设备环境尚未绑定测试实例：'+env)
        for b in matches:
            c=cs.get(b.get('caseId'))
            if not c or not any(i['id']==b.get('instanceId') and i.get('environment')==env for i in c['instances']):errors.append('invalid environment instance mapping')
    if p['routes']['uncoveredTransitionIds']:issues.append('未排入连续路线的迁移：'+str(len(p['routes']['uncoveredTransitionIds'])))
    if not p['routes']['searchComplete']:issues.append('有限域搜索达到资源上限，未完成部分不能声称不可达')
    if any(r['fixtureStatus']!='ready' for r in p['routes']['routes']):issues.append('继承路线的真实夹具、时钟、故障操作待完成准备')
    if any(r['contextStatus']=='not_modeled' for r in p['routes']['routes']):issues.append('缺少条件模型，路线只有结构可达证据')
    issues.extend(i['title'] for i in cfg['issues'] if not i.get('resolution'))
    if not cfg.get('upstreamApproved'):issues.append('上游需求分析尚未正式验收')
    for e in cfg['repository']['evidence']:
        path=Path(cfg['repository']['root'])/e['path']
        if not path.is_file():errors.append('missing code evidence '+e['path'])
        elif cfg['phase']=='planning' and sha(path.read_bytes())!=e['sha256']:errors.append('stale code reading '+e['path'])
    return {'planningDigest':p['planningDigest'],'codeDigest':p['codeDigest'],'mechanical':{'status':'PASS' if not errors else 'FAIL','errors':sorted(set(errors))},
            'readiness':{'status':'ready' if not errors and not issues else 'draft','issues':list(dict.fromkeys(issues))},
            'acceptance':{'status':'pending' if any(c['result']['status']!='passed' for c in cases) else 'passed','pending':sum(c['result']['status']=='pending' for c in cases),'failed':sum(c['result']['status']=='failed' for c in cases),'passed':sum(c['result']['status']=='passed' for c in cases)},
            'counts':{'states':len(m['states']),'stateEdges':len(m['transitions']),'primaryCases':len(m['requirements']),'regressionCases':len(cfg['regressions']),'testEdges':len(p['testGraph']['edges']),'entryCases':len(p['testGraph']['entryCaseIds']),'routes':len(p['routes']['routes']),'visits':p['routes']['visits'],'uncovered':len(p['routes']['uncoveredTransitionIds'])}}

def documents(p):
    s={s['id']:s['title'] for s in p['stateGraph']['nodes']};t={t['id']:t for t in p['stateGraph']['edges']}
    a=['# 测试设计与需求路线映射','', '阶段：'+{'planning':'规划','development':'开发','acceptance':'验收'}[p['phase']]+'。测试图逐项映射需求图，入口和连线保持一致；每项实际结果以证据为准。','', '## 连续验收顺序','',f"{len(p['routes']['routes'])} 段；{p['routes']['visits']} 次访问，{p['routes']['repeatedVisits']} 次重复；沿用输入的结构路线，未重新优化；不代表业务条件通过。",'']
    for i,r in enumerate(p['routes']['routes'],1):
        a.extend([f'### 流程 {i}：从{s[r["entryStateId"]]}进入','',r['preparation'],'','条件校验：'+{'conflict':'存在条件冲突，不能直接执行','passed':'已编码条件通过，仍需准备实际数据','finite_domain_passed':'已编码有限域条件通过，仍需准备实际数据','no_guard_constraints':'无附加条件，仍需准备实际数据','incomplete':'校验未完成','not_modeled':'条件未建模'}.get(r['contextStatus'],r['contextStatus']),'','每步先满足列出的条件，再执行操作，保留该项断言证据：',''])
        for n,step in enumerate(r['steps'],1):
            e=t[step['transitionId']];a.append(f'{n}. {s[e["from"]]} → {e["event"]}（{e["guard"]}）→ {s[e["to"]]}。验收项 `{step["caseId"]}`。')
        a.append('')
    if p['routes'].get('uncoveredDetails'):
        a.extend(['## 未排入连续路线的迁移',''])
        for missing in p['routes']['uncoveredDetails']:
            e=t[missing['transitionId']];a.append('- '+s[e['from']]+' → '+e['event']+' → '+s[e['to']]+'：'+missing['reason']+'。')
        a.append('')
    if p['harnessRoutes']:a.extend(['## 独立回归路线',''])
    elif p.get('regressionPolicy',{}).get('mode')=='deferred':a.extend(['本轮暂不纳入回归测试。',''])
    for h in p['harnessRoutes']:a.extend(['### '+h['title'],'','准备：'+'；'.join(h['setup']),'','操作：'+' → '.join(h['steps']),''])
    a.extend(['## 逐项测试设计',''])
    for c in p['cases']:
        status={'pending':'待验收','passed':'通过','failed':'失败'}[c['result']['status']]
        a.extend([f'### {c["title"]}',f'机器定位：`{c["id"]}`；{status}；准备状态：{c["readiness"]}。','', '**准备**：'+'；'.join(c['setup']),'','**操作**：'+' → '.join(c['steps']),'','**预期状态**：'+c['expectedState'],'','**功能预期**：'])
        a.extend('- '+x['text'] for x in c['assertions'] if x['kind']=='functional')
        a.extend(['','**视觉预期**：']+['- '+x['text'] for x in c['assertions'] if x['kind']=='visual'])
        a.extend(['','**视觉对应**：'+'；'.join(u.get('stateLabel','') for u in c['uiRefs']),'','**实测结论与证据**：'+status,''])
        if c['result'].get('staleEvidence'):a.append('旧观察已失效：'+c['result']['staleEvidence']['reason']+'；须复测，不能沿用通过。')
        for o in c['result'].get('observations',[]):a.append('- '+o['instanceId']+' / '+o['assertionId']+'：'+o['verdict']+'；'+o['actual']+'；'+'；'.join(e['path']+' @ '+e['locator'] for e in o['evidence']))
        if not c['result'].get('observations'):a.extend(['未执行，未采集。',''])
    b=['# 代码开发 Plan','',p['scope']['objective'],'','本阶段不实现应用代码、不执行产品验收。实现期间仅必要静态检查和单元测试；所有实现项完成后再进入完整验收。','', '## 现状与风险','']
    for e in p['repository']['evidence']:b.append(f'- `{e["path"]}`：{e["finding"]}')
    b.extend(['','## 实现顺序',''])
    for task in p['tasks']:
        b.extend([f'### {task["title"]}','',f'任务 `{task["id"]}`；依赖：'+(', '.join(task['dependsOn']) or '无'),'','位置：'+', '.join('`'+x+'`' for x in task['codePaths']),'','实施：'+'；'.join(task['approach']),'','完成条件：'+'；'.join(task['doneWhen']),'','必要开发检查：'])
        b.extend(f'- {c["kind"]}：`{c["command"]}` — {c["reason"]}' for c in task['checks']);b.append('')
    b.extend(['## 最终验收与待决','', '按 test-plan.json 的测试项及实例验收；继承路线先解决条件冲突与准备缺口，再执行产品功能/视觉验收。每项保留断言实测及证据定位。',''])
    if p.get('acceptanceMatrix'):b.extend(['设备矩阵：'+'；'.join(p['acceptanceMatrix'].get('environments',[])),'',p['acceptanceMatrix'].get('policy',''),''])
    b.extend('- '+i['title']+'：'+i['impact'] for i in p['issues'] if not i.get('resolution'))
    return '\n'.join(a),'\n'.join(b)

def build(root):
    root=Path(root);cfg=read(work(root));by,m,rg=load_inputs(cfg);p=assemble(cfg,by,m,rg);gate=check_model(root,cfg,p,m)
    from render import render
    docs=documents(p)
    write(root/'test-plan.json',p);write(root/'test-cases.md',docs[0]);write(root/'implementation-plan.md',docs[1]);write(root/'review.html',render(p,gate));write(root/'gate-result.json',gate)
    write(root/'_process/export-index.json',{'planningDigest':p['planningDigest'],'files':{n:sha((root/n).read_bytes()) for n in OUTPUTS}})
    return p,gate

def validate_current(root):
    root=Path(root);cfg=read(work(root));by,m,_=load_inputs(cfg);p=read(root/'test-plan.json')
    if p['planningDigest']!=plan_digest(cfg):raise ValueError('exports stale; build required')
    if p['codeDigest']!=code_digest(cfg):raise ValueError('code changed; rebuild and invalidate old evidence')
    index=read(root/'_process/export-index.json')
    if index.get('planningDigest')!=p['planningDigest'] or set(index.get('files',{}))!=set(OUTPUTS):raise ValueError('export index stale')
    for name,h in index['files'].items():
        if sha((root/name).read_bytes())!=h:raise ValueError('export modified: '+name)
    g=check_model(root,cfg,p,m);write(root/'gate-result.json',g);return cfg,p,g

def approved_plan(root,p):
    for file in ('review.json','approval.json'):
        r=read(Path(root)/'_process'/file)
        if r.get('planningDigest')!=p['planningDigest'] or r.get('status')!='PASS':raise ValueError('missing/current review or approval')
        if file=='review.json' and (r.get('context')!='independent' or not r.get('findings')):raise ValueError('independent review required')
        if file=='approval.json' and not r.get('humanReply'):raise ValueError('real human reply required')

def development_complete(root,cfg,p):
    for t in cfg['tasks']:
        if t['status']!='complete':raise ValueError('unfinished implementation task')
        for check in t['checks']:
            e=cfg.get('developmentEvidence',{}).get(t['id']+'/'+check['id'],{})
            if e.get('status')!='passed' or e.get('codeDigest')!=p['codeDigest'] or not evidence_ok(root,e):raise ValueError('missing/current development check evidence')

def advance_phase(root,target):
    cfg,p,g=validate_current(root)
    if g['mechanical']['status']!='PASS':raise ValueError('mechanical gate failed')
    if g['readiness']['status']!='ready':raise ValueError('planning readiness failed')
    approved_plan(root,p)
    if target=='development':
        if cfg['phase']!='planning' or g['readiness']['status']!='ready':raise ValueError('planning readiness failed')
    elif target=='acceptance':
        if cfg['phase']!='development':raise ValueError('must complete development first')
        development_complete(root,cfg,p)
    else:raise ValueError('unsupported target phase')
    cfg['phase']=target;write(work(root),cfg);build(root)

def record(root,result):
    cfg,p,g=validate_current(root)
    if cfg['phase']!='acceptance':raise ValueError('product acceptance is forbidden before all development completes')
    if g['mechanical']['status']!='PASS' or g['readiness']['status']!='ready':raise ValueError('current gates failed')
    approved_plan(root,p)
    development_complete(root,cfg,p)
    c=next((c for c in p['cases'] if c['id']==result.get('caseId')),None)
    if not c:raise ValueError('unknown case')
    errors=validate_result(root,p,c,result)
    if errors:raise ValueError('; '.join(errors))
    cfg['results'][c['id']]=result;write(work(root),cfg);build(root)

def invalidate(root,reason):
    if not reason:raise ValueError('invalidation reason required')
    cfg=read(work(root));old=read(Path(root)/'test-plan.json') if (Path(root)/'test-plan.json').exists() else {}
    for key,r in list(cfg.get('results',{}).items()):
        cfg['results'][key]={'status':'pending','actual':None,'evidence':[],
                            'staleEvidence':{'reason':reason,'codeDigest':r.get('codeDigest'),'observations':r.get('observations',[])}}
    cfg['phase']='development' if cfg['phase'] in ('development','acceptance') and old.get('planningDigest')==plan_digest(cfg) else 'planning'
    write(work(root),cfg);build(root)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['init','build','check','advance','record','invalidate']);ap.add_argument('root');ap.add_argument('extra',nargs='?');a=ap.parse_args();root=Path(a.root)
    if a.command=='init':
        if work(root).exists():raise ValueError('already initialized; maintain current file')
        write(work(root),{'phase':'planning','outputs':OUTPUTS,'scope':{},'inputs':[],'repository':{'root':'','exists':False,'evidence':[]},'issues':[],'tasks':[],'regressions':[],'overrides':{},'results':{},'upstreamApproved':False,'regressionPolicy':{'mode':'deferred','reason':'先映射需求主项；回归范围由用户确认'},'routePolicy':{'mode':'inherit_requirement_graph','resetAllowed':False,'resetReason':''}})
        print('initialized current working model');return
    if a.command=='build':_,g=build(root)
    elif a.command=='check':_,_,g=validate_current(root)
    elif a.command=='advance':advance_phase(root,a.extra);return
    elif a.command=='invalidate':invalidate(root,a.extra);return
    else:record(root,read(a.extra));return
    print(json.dumps({k:v for k,v in g.items() if k!='readiness'},ensure_ascii=False))
    if g['mechanical']['status']!='PASS':sys.exit(1)
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError) as e:print('BLOCKED: '+str(e),file=sys.stderr);sys.exit(2)
