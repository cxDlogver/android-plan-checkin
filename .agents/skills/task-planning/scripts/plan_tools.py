"""Task-plan artifacts, acceptance order and observation-integrity gates."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / 'references' / 'planning.schema.json'
REVIEW_RULES = {'semantics','case-oracles','fixtures-and-order','implementation-plan','verification-boundaries'}
LIMITATION = '规划门禁不执行应用测试；实际观察只能来自本次真实测试证据。DOM/样式契约不能证明真实浏览器布局与像素效果。'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def req_digest(m): return hashlib.sha256(canonical({k:v for k,v in m.items() if k not in ('reviews','reviewDigest')}).encode()).hexdigest()
def digest(m):
    core={k:v for k,v in m.items() if k not in ('reviews','reviewDigest','execution')}
    core['cases']=[{k:v for k,v in c.items() if k!='actualObservation'} for c in m['cases']]
    return hashlib.sha256(canonical(core).encode()).hexdigest()

def schema_errors(v,s,at='$'):
    checks={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'string':lambda x:isinstance(x,str),'integer':lambda x:isinstance(x,int) and not isinstance(x,bool),'boolean':lambda x:isinstance(x,bool),'null':lambda x:x is None}
    errors=[]
    if 'type' in s:
        kinds=s['type'] if isinstance(s['type'],list) else [s['type']]
        if not any(checks[k](v) for k in kinds):return [at+': wrong type']
    if 'const' in s and v!=s['const']:errors.append(at+': wrong constant')
    if 'enum' in s and v not in s['enum']:errors.append(at+': unknown enum')
    if isinstance(v,str):
        if len(v.strip())<s.get('minLength',0):errors.append(at+': empty value')
        if 'pattern' in s and not re.search(s['pattern'],v):errors.append(at+': pattern mismatch')
    if isinstance(v,int) and v<s.get('minimum',v):errors.append(at+': below minimum')
    if isinstance(v,dict):
        props=s.get('properties',{})
        errors += [at+': missing '+k for k in s.get('required',[]) if k not in v]
        if s.get('additionalProperties') is False:errors += [at+': unexpected '+k for k in v if k not in props]
        for k,item in v.items():
            if k in props:errors+=schema_errors(item,props[k],at+'.'+k)
    if isinstance(v,list):
        if len(v)<s.get('minItems',0):errors.append(at+': too few items')
        if s.get('uniqueItems') and len({canonical(x) for x in v})!=len(v):errors.append(at+': duplicate items')
        for i,item in enumerate(v):errors+=schema_errors(item,s.get('items',{}),at+'['+str(i)+']')
    return errors

def source_requirements(m,folder):
    s=m['source'];p=Path(folder)/s['requirementsPath'];g=Path(folder)/s['gatePath']
    raw,gate=read(p),read(g)
    errors=[]
    if sha(p)!=s['requirementsSha256']:errors.append('Requirements file SHA256 changed')
    if sha(g)!=s['gateSha256']:errors.append('Upstream gate file SHA256 changed')
    if req_digest(raw)!=s['requirementsDigest']:errors.append('Requirements semantic digest changed')
    if gate.get('result')!='PASS' or gate.get('modelDigest')!=s['requirementsDigest']:errors.append('Upstream gate is not PASS for this requirements version')
    if any(q.get('status')=='open' for q in raw.get('clarifications',[])):errors.append('Unresolved upstream clarification')
    return raw,errors

def entry_error(m,case_id,visits):
    if len(visits)>=len(m['traversal']['route']):return 'All planned visits already completed'
    if case_id != m['traversal']['route'][len(visits)]:return 'Attempted to skip/reorder the approved traversal'
    if not visits:
        if case_id not in m['graph']['roots']:return 'First case is not a root'
        root=next((c for c in m['cases'] if c['id']==case_id),None)
        if root is None or root['fixture']['externalPreconditions']:return 'Root has unmet external business preconditions'
        return None
    prev=visits[-1]
    if prev['status']!='pass':return 'Previous case did not pass; cannot enter next case'
    if (prev['caseId'],case_id) not in {(e['from'],e['to']) for e in m['graph']['edges']}:return 'No directed edge from immediately previous passed case'
    return None

def observation_errors(case,record,folder):
    errors=[];expected={e['id'] for e in case['expectedResults']}
    actual=[o['assertionId'] for o in record['observedValues']]
    results=[r['assertionId'] for r in record['assertionResults']]
    if record['status']=='not_run':
        if actual or results or record['evidence']:errors.append(case['id']+': not_run has fabricated observations/evidence')
        return errors
    if not actual or not results or not record['evidence']:errors.append(case['id']+': executed case lacks actual values, assertion results or evidence')
    if len(actual)!=len(set(actual)) or len(results)!=len(set(results)):errors.append(case['id']+': duplicate assertion observation')
    if not set(actual)<=expected or not set(results)<=expected:errors.append(case['id']+': unknown assertion observation')
    if record['status']=='pass':
        if set(actual)!=expected or set(results)!=expected:errors.append(case['id']+': pass must observe every expected assertion')
        if any(r['status']!='pass' for r in record['assertionResults']):errors.append(case['id']+': pass contains failed assertion')
        if any(e['exitCode']!=0 for e in record['evidence']):errors.append(case['id']+': pass contains nonzero command exit')
    if record['status']=='fail' and not any(r['status']=='fail' for r in record['assertionResults']) and not any(e['exitCode']!=0 for e in record['evidence']):errors.append(case['id']+': fail has no failing assertion or failed command')
    for ev in record['evidence']:
        p=Path(folder)/ev['path']
        try:
            if sha(p)!=ev['sha256']:errors.append(case['id']+': evidence hash mismatch')
        except OSError:errors.append(case['id']+': evidence file missing')
    return errors

def trace_errors(m,folder):
    run=m['execution'];errors=[];cases={c['id']:c for c in m['cases']}
    if run['modelDigest']!=digest(m):errors.append('Execution is bound to a different planning model')
    visits=run['visits']
    if not visits:
        if run['runId'] is not None or run['implementationRef'] is not None:errors.append('Unstarted execution must not claim a run or implementation')
    elif not run['runId'] or not run['implementationRef']:errors.append('Execution lacks run ID or implementation revision')
    prefix=[];latest={}
    for v in visits:
        err=entry_error(m,v['caseId'],prefix)
        if err:errors.append(err)
        if v['caseId'] not in cases:errors.append('Unknown visited case');continue
        if v['status']=='not_run':errors.append('A visit cannot be not_run')
        errors += observation_errors(cases[v['caseId']],v,folder)
        latest[v['caseId']]={k:x for k,x in v.items() if k!='caseId'}
        prefix.append(v)
    for c in m['cases']:
        errors += observation_errors(c,c['actualObservation'],folder)
        if c['id'] in latest:
            if c['actualObservation']!=latest[c['id']]:errors.append(c['id']+': actual record differs from latest run visit')
        elif c['actualObservation']['status']!='not_run':errors.append(c['id']+': pass/fail has no visit in this run')
    return errors

def execution_status(m):
    visits=m['execution']['visits']
    if not visits:return 'not_run'
    if visits[-1]['status']=='fail':return 'failed'
    if len(visits)==len(m['traversal']['route']):return 'passed'
    return 'in_progress'

def exports(m):
    head={k:m[k] for k in ('schemaVersion','analysisId','revision')};head['modelDigest']=digest(m)
    return {
      'test-cases.json':{**head,'executionPolicy':m['executionPolicy'],'cases':m['cases']},
      'test-case-graph.json':{**head,'nodes':[{'id':c['id'],'name':c['name'],'requirementIds':c['requirementIds'],'kind':c['kind'],'level':c['level']} for c in m['cases']], 'roots':m['graph']['roots'],'edges':m['graph']['edges'],'traversal':m['traversal']},
      'plan.json':{**head,**m['plan']},
      'execution-record.json':{**head,'executionStatus':execution_status(m),'run':m['execution'],'cases':[{'caseId':c['id'],**c['actualObservation']} for c in m['cases']]},
    }

def esc(x):return str(x).replace('|','&#124;').replace('\n','<br>')
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(esc(v) for v in row)+' |' for row in rows])
def label(x):return str(x).replace('&','&amp;').replace('"','&quot;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
def docs(m):
    prefix='版本：'+str(m['revision'])+'；规划摘要：'+digest(m)+'\n\n'
    tc='# Test Case 验收规范\n\n'+prefix+'默认使用单元测试与集成测试，不启动浏览器。每项的数据夹具在本用例内显式准备和清理；实际验收结果必须经当前运行的前序 PASS 沿图边进入。\n\n'
    for c in m['cases']:
        tc+='## '+c['id']+' '+c['name']+'\n\n类型：'+c['kind']+'；层级：'+c['level']+'；环境：'+c['environment']+'\n\n来源：'+', '.join(c['requirementIds'])+'；映射理由：'+c['mappingRationale']+'\n\n'
        tc+='夹具准备：\n\n'+'\n'.join('- '+s for s in c['fixture']['setup'])+'\n\n清理：\n\n'+'\n'.join('- '+s for s in c['fixture']['cleanup'])+'\n\n外部业务前置：'+('；'.join(c['fixture']['externalPreconditions']) or '无')+'\n\n'
        tc+='验收步骤：\n\n'+table(['步骤','动作','观测断言'],[(s['id'],s['action'],', '.join(s['expectedResultIds'])) for s in c['steps']])+'\n\n'
        tc+='预期期望：\n\n'+table(['断言','预期','观测方法','来源标准'],[(e['id'],e['expected'],e['observe'],', '.join(e['criterionRefs'])) for e in c['expectedResults']])+'\n\n'
        tc+='实际观察：'+c['actualObservation']['status']+'；'+c['actualObservation']['note']+'\n\n观测值：'+canonical(c['actualObservation']['observedValues'])+'\n\n断言结果：'+canonical(c['actualObservation']['assertionResults'])+'\n\n证据：'+canonical(c['actualObservation']['evidence'])+'\n\n计划测试文件：'+c['testFile']+'\n\n计划命令：'+c['plannedCommand']+'\n\n局限：'+('；'.join(c['limitations']) or '无额外局限')+'\n\n'
    fence=chr(96)*3;graph=['flowchart TD']
    for c in m['cases']:graph.append('  '+c['id']+'["'+label(c['id']+' '+c['name'])+('〔起始〕' if c['id'] in m['graph']['roots'] else '')+'"]')
    for e in m['graph']['edges']:graph.append('  '+e['from']+' --> '+e['to'])
    gd='# Test Case 有向验收图\n\n'+prefix+'边表示本次验收顺序，前序未 PASS 不允许进入后序；不表示业务状态自动继承，也不等同开发任务依赖。\n\n'+fence+'mermaid\n'+'\n'.join(graph)+'\n'+fence+'\n\n'
    gd+='## 最少重复遍历\n\n'+m['traversal']['proof']+'\n\n路线：'+' → '.join(m['traversal']['route'])+'\n\n'+table(['前序','后序','顺序理由'],[(e['from'],e['to'],e['reason']) for e in m['graph']['edges']])+'\n'
    p=m['plan'];pd='# 代码实现计划\n\n'+prefix+p['objective']+'\n\n## 当前基线\n\n'+p['baseline']+'\n\n## 设计与选型\n\n'+table(['议题','选择','理由'],[(d['topic'],d['choice'],d['rationale']) for d in p['decisions']])+'\n\n'
    pd+='## 模块与文件\n\n'+table(['计划路径','职责'],[(x['path'],x['responsibility']) for x in p['modules']])+'\n\n'
    for t in p['tasks']:
        pd+='## '+t['id']+' '+t['title']+'\n\n状态：'+t['status']+'；开发前置：'+(', '.join(t['dependsOn']) or '无')+'\n\n需求：'+', '.join(t['requirementIds'])+'\n\n用例：'+', '.join(t['caseIds'])+'\n\n输出：'+'；'.join(t['outputs'])+'\n\n实现步骤：\n\n'+'\n'.join('- '+s for s in t['steps'])+'\n\n完成标准：\n\n'+'\n'.join('- '+s for s in t['doneCriteria'])+'\n\n'
    pd+='## 计划命令（尚未执行）\n\n'+table(['用途','命令'],[(c['purpose'],c['command']) for c in p['commands']])+'\n\n## 验证边界\n\n'+'\n'.join('- '+v for v in p['verificationLimitations'])+'\n\n## 选型依据\n\n'+'\n'.join('- ['+r['title']+']('+r['url']+')' for r in p['references'])+'\n'
    ex='# 实际执行与观察记录\n\n'+prefix+'应用验收执行状态：**'+execution_status(m)+'**\n\n'+LIMITATION+'\n\n'+table(['用例','状态','观测值','证据数'],[(c['id'],c['actualObservation']['status'],canonical(c['actualObservation']['observedValues']),len(c['actualObservation']['evidence'])) for c in m['cases']])+'\n\n当前运行：'+canonical(m['execution'])+'\n'
    return {'test-cases.md':tc,'test-case-graph.md':gd,'plan.md':pd,'execution-record.md':ex}

def render(m,p):
    errors=schema_errors(m,read(SCHEMA))
    if errors:raise ValueError('\n'.join(errors))
    for name,v in exports(m).items():dump(Path(p).parent/name,v)
    for name,text in docs(m).items():(Path(p).parent/name).write_text(text,encoding='utf-8')

def gate(m,p,check_artifacts=True):
    folder=Path(p).parent;checks=[]
    def add(key,errors):checks.append({'id':key,'result':'FAIL' if errors else 'PASS','issues':errors})
    errors=schema_errors(m,read(SCHEMA));add('schema',errors)
    if errors:return {'planningStatus':'FAIL','executionStatus':'invalid','checks':checks,'limitation':LIMITATION}
    try:source,errors=source_requirements(m,folder)
    except (OSError,ValueError,KeyError) as e:source={};errors=[str(e)]
    add('source-and-upstream-gate',errors)
    atom={r['id']:r for r in source.get('atomicRequirements',[])};non={r['id']:r for r in source.get('nonTransitionRequirements',[])};reqs={**atom,**non}
    cases={c['id']:c for c in m['cases']};caseids=set(cases);taskids=[t['id'] for t in m['plan']['tasks']]
    ids=[c['id'] for c in m['cases']]+taskids
    add('unique-ids',[i for i,n in Counter(ids).items() if n>1]+[i for i in ids if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',i)])
    mapping=[]
    for r in atom:
        if sum(c['kind']=='primary' and c['requirementIds']==[r] for c in m['cases'])!=1:mapping.append(r+': need exactly one primary case')
    for r in non:
        if sum(c['kind']=='supporting' and c['requirementIds']==[r] for c in m['cases'])!=1:mapping.append(r+': need exactly one supporting case')
    for c in m['cases']:
        if any(r not in reqs for r in c['requirementIds']):mapping.append(c['id']+': unknown requirement')
        if c['kind']=='primary' and (len(c['requirementIds'])!=1 or c['requirementIds'][0] not in atom):mapping.append(c['id']+': invalid primary mapping')
        if c['kind']=='supporting' and (len(c['requirementIds'])!=1 or c['requirementIds'][0] not in non):mapping.append(c['id']+': invalid supporting mapping')
        if c['kind']=='scenario' and (len(c['requirementIds'])<2 or any(r not in atom for r in c['requirementIds'])):mapping.append(c['id']+': scenario must justify multiple atomic requirements')
    add('requirement-case-mapping',mapping)
    oracle_errors=[]
    for c in m['cases']:
        expected_refs=set()
        for rid in c['requirementIds']:
            if rid in reqs:
                r=reqs[rid]
                expected_refs.update(rid+':F:'+str(i) for i in range(len(r['functionalRequirements']['acceptanceCriteria'])))
                expected_refs.update(rid+':V:'+str(i) for i in range(len(r['visualRequirements']['criteria'])))
        refs={r for e in c['expectedResults'] for r in e['criterionRefs']}
        if refs!=expected_refs:oracle_errors.append(c['id']+': criterion mapping missing or unsupported')
        step_ids=[s['id'] for s in c['steps']]
        if len(set(step_ids))!=len(step_ids):oracle_errors.append(c['id']+': duplicate acceptance step ID')
        aids=[e['id'] for e in c['expectedResults']]
        if len(set(aids))!=len(aids):oracle_errors.append(c['id']+': duplicate expected assertion')
        step_refs={x for s in c['steps'] for x in s['expectedResultIds']}
        if step_refs!=set(aids):oracle_errors.append(c['id']+': acceptance steps do not observe exactly all assertions')
        if len(c['steps'])<4:oracle_errors.append(c['id']+': missing preparation/action/observation/cleanup steps')
        if c['level'] not in m['executionPolicy']['allowedLevels']:oracle_errors.append(c['id']+': disallowed test level')
        if any(x in c['environment'].lower() for x in ('playwright','puppeteer','selenium','browser-mode')):oracle_errors.append(c['id']+': browser acceptance is disabled')
    add('expected-observed-steps-and-no-browser',oracle_errors)
    edges=[(e['from'],e['to']) for e in m['graph']['edges']];roots=set(m['graph']['roots']);graph_errors=[]
    if len(edges)!=len(set(edges)):graph_errors.append('Duplicate acceptance edge')
    for left,right in edges:
        if left not in caseids or right not in caseids:graph_errors.append('Unknown test-graph endpoint')
    for root in roots:
        if root not in cases:graph_errors.append('Unknown root')
        else:
            if cases[root]['fixture']['externalPreconditions']:graph_errors.append(root+': root has external business preconditions')
            if any(right==root for left,right in edges):graph_errors.append(root+': root has incoming edge')
    seen=set(roots);queue=deque(roots)
    while queue:
        at=queue.popleft()
        for left,right in edges:
            if left==at and right not in seen:seen.add(right);queue.append(right)
    if seen!=caseids:graph_errors.append('Unreachable/missing cases from graph roots')
    if any(not any(right==cid for left,right in edges) for cid in caseids-roots):graph_errors.append('Non-root case has no incoming acceptance edge')
    add('directed-graph-entry',graph_errors)
    route=m['traversal']['route'];tr=m['traversal'];route_errors=[]
    if set(route)!=caseids:route_errors.append('Traversal must cover all and only case nodes')
    if not route or route[0] not in roots:route_errors.append('Traversal must begin at root')
    if any((a,b) not in set(edges) for a,b in zip(route,route[1:])):route_errors.append('Traversal jumps over a missing edge')
    repeats=len(route)-len(set(route))
    if tr['repeatCount']!=repeats:route_errors.append('Incorrect repeated visit count')
    if tr['lowerBoundVisits']!=len(caseids):route_errors.append('Incorrect distinct-node visit lower bound')
    if tr['optimality']=='proven_optimal' and (repeats or len(route)!=len(caseids)):route_errors.append('No valid zero-repeat optimality certificate')
    add('traversal-and-minimum-repeat-proof',route_errors)
    plan_errors=[];tasks={t['id']:t for t in m['plan']['tasks']};remaining=set(tasks);done=set()
    for t in tasks.values():
        if any(d not in tasks for d in t['dependsOn']):plan_errors.append(t['id']+': missing development dependency')
        if any(r not in reqs for r in t['requirementIds']):plan_errors.append(t['id']+': unknown task requirement')
        if any(c not in cases for c in t['caseIds']):plan_errors.append(t['id']+': unknown task case')
    while remaining:
        ready={i for i in remaining if set(tasks[i]['dependsOn'])<=done}
        if not ready:plan_errors.append('Development task dependency cycle');break
        done|=ready;remaining-=ready
    if {r for t in tasks.values() for r in t['requirementIds']}!=set(reqs):plan_errors.append('Implementation plan does not cover all requirements')
    if {c for t in tasks.values() for c in t['caseIds']}!=caseids:plan_errors.append('Implementation plan does not cover all cases')
    if not m['plan']['verificationLimitations']:plan_errors.append('Default verification boundaries must be explicit')
    add('implementation-plan-completeness',plan_errors)
    add('actual-observations-and-runtime-entry',trace_errors(m,folder))
    review_errors=[]
    if {r['ruleId'] for r in m['reviews']}!=REVIEW_RULES or any(r['result']!='pass' for r in m['reviews']):review_errors.append('Missing/failed semantic review')
    if m['reviewDigest']!=digest(m):review_errors.append('Stale/missing planning semantic review digest')
    add('semantic-review',review_errors)
    if check_artifacts:
        errors=[]
        for name,v in exports(m).items():
            try:
                if read(folder/name)!=v:errors.append(name+': JSON drift')
            except (OSError,ValueError):errors.append(name+': missing/invalid JSON')
        for name,text in docs(m).items():
            try:
                if (folder/name).read_text(encoding='utf-8')!=text:errors.append(name+': Markdown drift')
            except OSError:errors.append(name+': missing Markdown')
        add('complete-synchronized-artifacts',errors)
    return {'schemaVersion':m['schemaVersion'],'analysisId':m['analysisId'],'revision':m['revision'],'modelDigest':digest(m),
            'planningStatus':'FAIL' if any(c['result']=='FAIL' for c in checks) else 'PASS','executionStatus':execution_status(m),
            'counts':{'primaryCases':sum(c['kind']=='primary' for c in m['cases']),'supportingCases':sum(c['kind']=='supporting' for c in m['cases']),'scenarioCases':sum(c['kind']=='scenario' for c in m['cases']),'cases':len(cases),'edges':len(edges),'plannedVisits':len(route),'repeatVisits':repeats,'implementationTasks':len(tasks)},'checks':checks,'limitation':LIMITATION}

def report(m,p):
    r=gate(m,p);folder=Path(p).parent;dump(folder/'gate-report.json',r)
    text='# 任务规划门禁报告\n\n规划门禁：**'+r['planningStatus']+'**\n\n应用验收执行：**'+r['executionStatus']+'**\n\n'+LIMITATION+'\n\n'+table(['检查','结果','问题'],[(c['id'],c['result'],'；'.join(c['issues']) or '无') for c in r['checks']])+'\n\n统计：'+canonical(r.get('counts',{}))+'\n'
    (folder/'gate-report.md').write_text(text,encoding='utf-8');return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['render','digest','gate','next']);p.add_argument('model');args=p.parse_args()
    try:
        m=read(args.model)
        if args.command=='digest':print(digest(m));return 0
        if args.command=='render':render(m,args.model);print('Planning artifacts rendered');return 0
        if args.command=='next':
            errors=schema_errors(m,read(SCHEMA))
            if not errors:
                readiness=gate(m,args.model,check_artifacts=False)
                errors=[issue for check in readiness['checks'] for issue in check['issues']]
            if errors:raise ValueError('\n'.join(errors))
            visits=m['execution']['visits'];route=m['traversal']['route']
            if len(visits)>=len(route):print('No remaining case');return 0
            cid=route[len(visits)];err=entry_error(m,cid,visits)
            if err:raise ValueError(err)
            print(cid);return 0
        r=report(m,args.model);print(json.dumps({'planningStatus':r['planningStatus'],'executionStatus':r['executionStatus'],'counts':r.get('counts'),'issues':[c for c in r['checks'] if c['result']!='PASS']},ensure_ascii=False));return 0 if r['planningStatus']=='PASS' else 2
    except (OSError,ValueError,KeyError) as e:print(str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
