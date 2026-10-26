#!/usr/bin/env python3
"""Validate planning data; derive a proven minimum-visit test graph and read-only views."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
UPSTREAM=SKILL.parent/'requirement-analysis'/'scripts'
sys.path.insert(0,str(UPSTREAM))
from analyze import canonical, digest, load_json, raw_hash, resolve_file, schema_errors, pointer, lookup
from atomic import evaluate as evaluate_atomic
from coverage_route import minimum_visit_plan

CATEGORIES=('schema','inputs','one-to-one','data-mock','acceptance','code-task','regression','route','views')

def selected_text(file,locator):
    text=file.read_text(encoding='utf-8-sig').replace('\r\n','\n')
    m=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',locator)
    if m:
        start,end=int(m[1]),int(m[2] or m[1]);lines=text.splitlines()
        if not 1<=start<=end<=len(lines): raise ValueError('Invalid line range '+locator)
        return '\n'.join(lines[start-1:end])
    if file.suffix.lower()=='.json': return canonical(pointer(json.loads(text),locator))
    if locator!='$' and locator not in text: raise ValueError('Missing heading '+locator)
    return text

def check_source(ref,path,workspace):
    file=resolve_file(path,ref['path'],workspace)
    if raw_hash(file.read_bytes())!=ref['sha256']: raise ValueError('Stale source '+ref['path'])
    selected=selected_text(file,ref['locator'])
    if 'excerpt' in ref and ref['excerpt'].replace('\r\n','\n') not in selected: raise ValueError('Excerpt outside locator '+ref['path'])
    return selected

def safe_target(path,raw,workspace):
    if re.match(r'^[a-z][a-z0-9+.-]*:',raw,re.I) or Path(raw).is_absolute() or raw.startswith(('//','\\\\')):
        raise ValueError('File must be workspace-relative: '+raw)
    target=(path.parent/raw).resolve();target.relative_to(workspace.resolve())
    return target

def indexed(items,label,errors):
    result={}
    for item in items:
        if item['id'] in result: errors.append('Duplicate '+label+' '+item['id'])
        result[item['id']]=item
    return result

def value_contract(value,label,errors,typ=None):
    if value['mode']=='literal':
        if 'value' not in value or 'resolve' in value or 'oracle' in value: errors.append(label+': literal needs only value')
        elif typ in ('string','date','datetime','time') and not isinstance(value['value'],str): errors.append(label+': wrong literal type')
        elif typ in ('integer','number') and (isinstance(value['value'],bool) or not isinstance(value['value'],(int,float)) or typ=='integer' and int(value['value'])!=value['value']): errors.append(label+': wrong literal type')
        elif typ=='boolean' and not isinstance(value['value'],bool): errors.append(label+': wrong literal type')
        elif typ=='array' and not isinstance(value['value'],list): errors.append(label+': wrong literal type')
        elif typ=='object' and not isinstance(value['value'],dict): errors.append(label+': wrong literal type')
    elif 'value' in value or not value.get('resolve') or not value.get('oracle'): errors.append(label+': context needs resolve/oracle and no fixed value')

def endpoints(case,transitions,requirements,states):
    if case['kind']=='primary':
        t=transitions[requirements[case['requirementId']]['transitionId']]
        return ('state',t['from']),('state',t['to']),states[t['from']]['isInitial']
    return ('fixture',case['id']),('checked',case['id']),True

def derive_route(model,state_model,atomic_model):
    requirements={r['id']:r for r in atomic_model['requirements']};transitions={t['id']:t for t in state_model['transitions']};states={s['id']:s for s in state_model['states']}
    primary={c['requirementId']:c['id'] for c in model['cases'] if c['kind']=='primary'}
    sequence=[primary[r] for r in atomic_model['coverage']['sequence']]+sorted(c['id'] for c in model['cases'] if c['kind']!='primary')
    ends={c['id']:endpoints(c,transitions,requirements,states) for c in model['cases']}
    # Independent fixtures have distinct identities, cannot bridge to noninitial primary states.
    calc_states={};calc_edges=[]
    for cid,(start,end,initial) in sorted(ends.items()):
        calc_states.setdefault(start,{'id':canonical(start),'isInitial':initial});calc_states.setdefault(end,{'id':canonical(end),'isInitial':False})
        calc_edges.append({'id':cid,'from':canonical(start),'to':canonical(end)})
    # Mark initial states after insertion: a prior target may also be a genuine initial state.
    for start,end,initial in ends.values():
        if initial: calc_states[start]['isInitial']=True
    _,minimum=minimum_visit_plan({'states':list(calc_states.values()),'transitions':calc_edges})
    lower=atomic_model['coverage']['minimumVisitCount']+sum(c['kind']!='primary' for c in model['cases'])
    if minimum!=lower or len(sequence)!=minimum: raise ValueError('Independent-case lower bound did not match exact optimizer')
    edges=[];seen=set()
    for a,b in zip(sequence,sequence[1:]):
        if (a,b) in seen: continue
        seen.add((a,b));edge={'id':'E'+str(len(edges)+1).zfill(6),'from':a,'to':b}
        if ends[a][1]==ends[b][0]: edge.update(kind='handoff',viaStateId=ends[a][1][1])
        elif ends[b][2]: edge['kind']='restart'
        else: raise ValueError('Illegal case entry '+a+' -> '+b)
        edges.append(edge)
    coverage={'algorithm':'inherited-optimum-plus-independent-cases','optimality':'proven','sequence':sequence,'visitCount':minimum,'minimumVisitCount':minimum,'primaryMinimumVisitCount':atomic_model['coverage']['minimumVisitCount'],'additionalVisitCount':minimum-len(model['cases'])}
    return edges,coverage

def embedded(data): return canonical(data).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')

def html_text(model,state_model,task_plan,atomic_model):
    template=(SKILL/'assets'/'test-cases.template.html').read_text(encoding='utf-8')
    for key,value in {'__MODEL_SHA__':digest(model),'__MODEL_JSON__':embedded(model),'__STATE_MODEL_JSON__':embedded(state_model),'__TASK_PLAN_JSON__':embedded(task_plan),'__ATOMIC_MODEL_JSON__':embedded(atomic_model)}.items(): template=template.replace(key,value)
    return template

def md_text(plan,model):
    def fmt(items):
        result=[];i=0
        while i<len(items):
            m=re.fullmatch(r'(.*?)(\d+)',items[i]);j=i+1
            if m:
                while j<len(items):
                    n=re.fullmatch(r'(.*?)(\d+)',items[j])
                    if not n or n[1]!=m[1] or int(n[2])!=int(m[2])+j-i: break
                    j+=1
            if j-i>=4: result.append(items[i]+'～'+items[j-1]+'（连续ID）');i=j
            else: result.append(items[i]);i+=1
        return '、'.join(result) or '无'
    initial=all(t['status']=='planned' for t in plan['tasks']) and all(c['execution']['status']=='not_run' for c in model['cases'])
    labels={'planned':'待实施','implemented':'已实现待验收','not_run':'未执行','running':'执行中','passed':'通过','failed':'未通过','partial':'部分完成','blocked':'暂不能执行','stale':'证据已失效'}
    def counts(values):
        return '、'.join(labels.get(v,v)+' '+str(values.count(v)) for v in dict.fromkeys(values))
    summary='规划状态：全部任务 planned；全部用例 not_run。本文由 task-plan.json 生成。' if initial else '执行状态：任务 '+counts([t['status'] for t in plan['tasks']])+'；用例 '+counts([c['execution']['status'] for c in model['cases']])+'。本文由 task-plan.json 生成。'
    lines=['# '+plan['title'],'',summary,'',
           '原子需求 '+str(sum(c['kind']=='primary' for c in model['cases']))+' 项；补充用例 '+str(sum(c['kind']!='primary' for c in model['cases']))+' 项；最少 '+str(model['coverage']['visitCount'])+' 次逻辑用例访问，其中重复 '+str(model['coverage']['additionalVisitCount'])+' 次。','',
           '[Test Case 图](test-cases.html) · [Test Case JSON](test-cases.json) · [任务 JSON](task-plan.json)','',
           '## 输入依据','']
    for field in ('stateGraph','atomicGraph'):
        r=model[field];lines.append('- '+field+'：['+r['path']+']('+r['path']+')，canonical SHA-256 '+r['sha256'])
    for r in model['inputs']: lines.append('- '+r['role']+'：['+r['path']+']('+r['path']+') · '+r['locator']+' · SHA-256 '+r['sha256'])
    lines+=['','## 执行前置项','']
    for p in plan['prerequisites']: lines+=['- **'+p['id']+' · '+p['status']+'**：'+p['description'],'  补足标准：'+p['resolution'],'  影响用例：'+fmt(p['affects'])]
    lines+=['','## 代码链路证据','']
    for e in plan['codeEvidence']: lines.append('- '+e['id']+'：['+e['path']+']('+e['path']+') · '+e['locator']+'；'+e['role']+'；SHA-256 '+e['sha256'])
    lines+=['','## 直接影响与回归范围','']
    for i in plan['impacts']: lines+=['- **'+i['id']+' · '+i['decision']+'**：'+i['behavior'],'  机制：'+i['mechanism'],'  暴露输入：'+i['exposure'],'  判断：'+i['reason'],'  用例：'+fmt(i['testCaseIds'])]
    for t in plan['tasks']:
        lines+=['','## '+t['id']+' · '+t['title'],'',t['goal'],'','依赖：'+fmt(t['dependsOn']),'','文件范围：','']
        for f in t['files']: lines.append('- '+f['change']+' ['+f['path']+']('+f['path']+')：'+f['purpose'])
        lines+=['','实施步骤：','']+[str(n+1)+'. '+s for n,s in enumerate(t['steps'])]
        lines+=['','Test Case：'+fmt(t['testCaseIds']),'','原子需求：'+fmt(t['requirementIds']),'','完成标准：','']+['- '+s for s in t['done']]
        lines+=['','计划检查（均未执行）：' if initial else '任务状态：'+labels[t['status']]+'；计划检查：','']+['- '+c['command']+'；前置任务：'+fmt(c['requires'])+('' if initial else '；'+labels[c['status']]) for c in t['checks']]
    return '\n'.join(lines)+'\n'

def check_acceptance(case,transition,states,errors):
    groups=case['acceptance'];label=case['id']
    if not any(g['applicable'] for g in groups.values()): errors.append(label+': at least one acceptance aspect must apply')
    if transition:
        for name,facts in (('visual','visualFacts'),('functional','functionalFacts')):
            if any(states[sid][facts] for sid in (transition['from'],transition['to'])) and not groups[name]['applicable']:
                errors.append(label+': '+name+' facts require applicable acceptance')
    for name,group in groups.items():
        if group['applicable']!=bool(group['checks']): errors.append(label+': '+name+' applicability must agree with checks')
        for check in group['checks']:
            forms={e['form'] for e in check['evidence']};env=check['environment']
            if 'assertion-report' not in forms: errors.append(label+': each check needs expected/actual assertion evidence')
            if (check['testType']=='browser')!=(env=='browser'): errors.append(label+': browser acceptance requires browser environment; script acceptance uses runtime or native')
            if 'dom' in forms and env!='browser': errors.append(label+': DOM evidence requires browser environment')
            if 'native-tree' in forms and env!='native': errors.append(label+': native tree requires native environment')
            if forms&{'screenshot','layout-measurement'} and env not in ('browser','native'): errors.append(label+': rendered evidence requires an actual UI host')

def evaluate(model,path,workspace,with_views=False,task_plan=None):
    checks={k:[] for k in CATEGORIES}
    def result(): return {'scope':'planning-artifacts-only','status':'failed' if any(checks.values()) else 'passed','checks':[{'id':k,'status':'failed' if v else 'not-tested' if k=='views' and not with_views else 'passed','findings':v} for k,v in checks.items()]}
    def fail(k,msg): checks[k].append(msg)
    plan_path=path.parent/'task-plan.json'
    try:
        plan=load_json(plan_path) if task_plan is None else task_plan
        checks['schema']=schema_errors(model,load_json(SKILL/'assets'/'test-cases.schema.json'))+schema_errors(plan,load_json(SKILL/'assets'/'task-plan.schema.json'))
    except (OSError,ValueError) as exc: fail('schema',str(exc));return result()
    if checks['schema']: return result()
    if any(c['execution'] != {'status':'not_run','actual':None,'evidence':[]} for c in model['cases']) or any(t['status']!='planned' or any(c['status']!='not_run' for c in t['checks']) for t in plan['tasks']):
        fail('schema','Planning requires planned/not_run records; use code-execution to validate execution results')
        return result()
    try:
        state_path=resolve_file(path,model['stateGraph']['path'],workspace);atomic_path=resolve_file(path,model['atomicGraph']['path'],workspace)
        state=load_json(state_path);atomic=load_json(atomic_path)
        upstream=evaluate_atomic(atomic,atomic_path,workspace,with_html=False)
        if upstream['status']!='passed': fail('inputs',upstream)
        if digest(state)!=model['stateGraph']['sha256'] or digest(atomic)!=model['atomicGraph']['sha256']: fail('inputs','Upstream canonical digest mismatch')
        if resolve_file(atomic_path,atomic['stateGraph']['path'],workspace)!=state_path: fail('inputs','Atomic graph binds a different state graph')
        if model['revision']!=state['revision'] or plan['revision']!=model['revision']: fail('inputs','Revision must match the bound state graph')
        if resolve_file(plan_path,plan['testCases']['path'],workspace)!=path.resolve() or plan['testCases']['sha256']!=digest(model): fail('inputs','Task plan binds a different test graph or digest')
        for ref in model['inputs']: check_source(ref,path,workspace)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc: fail('inputs',str(exc))
    if checks['inputs']: return result()
    cases=indexed(model['cases'],'case',checks['one-to-one']);profiles=indexed(model['dataProfiles'],'profile',checks['data-mock'])
    indexed(model['inputs'],'input',checks['inputs'])
    requirements={r['id']:r for r in atomic['requirements']};transitions={t['id']:t for t in state['transitions']};states={s['id']:s for s in state['states']};constraints={c['id'] for c in state['constraints']}
    primary=[c for c in model['cases'] if c['kind']=='primary']
    if len(primary)!=len(requirements) or {c['requirementId'] for c in primary}!=set(requirements): fail('one-to-one','Exactly one primary case per atomic requirement is required')
    for profile in profiles.values():
        names=set()
        for field in profile['fields']:
            if field['name'] in names: fail('data-mock','Duplicate field '+field['name'])
            names.add(field['name']);value_contract(field,profile['id']+'.'+field['name'],checks['data-mock'],field['type'])
            try: check_source(field['source'],path,workspace)
            except (OSError,ValueError,KeyError,IndexError,TypeError) as exc: fail('data-mock',str(exc))
    for c in cases.values():
        label=c['id'];t=None
        if c['kind']=='primary':
            r=requirements.get(c['requirementId']);t=transitions.get(r['transitionId']) if r else None
            if not t: fail('one-to-one',label+': unknown atomic requirement');continue
            if c['given']['stateId']!=t['from'] or c['expected']['stateId']!=t['to'] or c['operation']!=t['operation']: fail('one-to-one',label+': changed initial state, operation or final state')
            if c['impactId'] is not None or c['constraintIds']: fail('one-to-one',label+': primary case must not duplicate independent coverage')
        elif c['requirementId'] is not None or c['given']['stateId'] is not None or c['expected']['stateId'] is not None: fail('one-to-one',label+': independent cases cannot impersonate business transitions')
        if c['dataProfileId'] not in profiles: fail('data-mock',label+': unknown data profile')
        elif c['kind']!='primary' and profiles[c['dataProfileId']]['scope']!='case': fail('data-mock',label+': independent fixture needs case-scoped data')
        for m in c['mocks']:
            value_contract(m['response'],label+'.mock',checks['data-mock'])
            if 'matches' in m and not (t and t.get('condition')): fail('data-mock',label+': branch witness without a condition')
        if t and t.get('condition'):
            cond=t['condition'];witnesses=[m['response'].get('value') if m['response']['mode']=='literal' else m.get('matches') for m in c['mocks']]
            def matches(w):
                if not isinstance(w,dict): return False
                for key,allowed in cond['match'].items():
                    ok,value=lookup(w,key)
                    if not ok or canonical(value) not in {canonical(x) for x in allowed}: return False
                return True
            if not any(matches(w) for w in witnesses): fail('data-mock',label+': missing branch result preparation or matching witness')
        check_acceptance(c,t,states,checks['acceptance'])
        if not set(c['constraintIds'])<=constraints: fail('acceptance',label+': unknown constraint')
        if c['kind']=='constraint' and (not c['constraintIds'] or c['impactId'] is not None): fail('acceptance',label+': constraint case needs rule coverage only')
        if c['kind']=='regression' and (c['impactId'] is None or c['constraintIds']): fail('regression',label+': regression case needs a direct impact only')
    covered=set(x for c in cases.values() for x in c['constraintIds'])
    if covered!=constraints: fail('acceptance','All global constraints need dedicated acceptance coverage')
    evidence=indexed(plan['codeEvidence'],'code evidence',checks['code-task']);tasks=indexed(plan['tasks'],'task',checks['code-task']);impacts=indexed(plan['impacts'],'impact',checks['regression'])
    indexed(plan['prerequisites'],'prerequisite',checks['code-task'])
    for e in evidence.values():
        try: check_source(e,plan_path,workspace)
        except (OSError,ValueError,KeyError,IndexError,TypeError) as exc: fail('code-task',str(exc))
    all_modified=set();all_mapped=set()
    for task in tasks.values():
        if not set(task['dependsOn'])<=set(tasks) or task['id'] in task['dependsOn']: fail('code-task',task['id']+': invalid dependencies')
        tc=set(task['testCaseIds']);all_mapped|=tc
        if not tc<=set(cases): fail('code-task',task['id']+': unknown test case')
        expected={cases[x]['requirementId'] for x in tc if x in cases and cases[x]['requirementId'] is not None}
        if set(task['requirementIds'])!=expected: fail('code-task',task['id']+': requirement mapping does not equal case mapping')
        for file in task['files']:
            try:
                target=safe_target(plan_path,file['path'],workspace)
                if file['change']=='create':
                    if target.exists() or file['evidenceIds']: fail('code-task','Create path already exists or claims current code evidence: '+file['path'])
                else:
                    if not target.is_file() or not file['evidenceIds']: fail('code-task','Existing file needs direct evidence: '+file['path'])
                    for eid in file['evidenceIds']:
                        if eid not in evidence or safe_target(plan_path,evidence[eid]['path'],workspace)!=target: fail('code-task','Wrong file evidence '+eid)
                if file['change']!='read': all_modified.add(file['path'])
            except (ValueError,OSError) as exc: fail('code-task',str(exc))
        for check in task['checks']:
            if not set(check['requires'])<=set(tasks): fail('code-task',task['id']+': check requires unknown task')
    if all_mapped!=set(cases): fail('code-task','Every case must have a responsible task')
    visiting=set();visited=set()
    def visit(tid):
        if tid in visiting: fail('code-task','Task dependency cycle at '+tid);return
        if tid in visited or tid not in tasks:return
        visiting.add(tid)
        for dep in tasks[tid]['dependsOn']: visit(dep)
        visiting.remove(tid);visited.add(tid)
    for tid in tasks: visit(tid)
    for p in plan['prerequisites']:
        if not set(p['affects'])<=set(cases): fail('code-task','Prerequisite maps unknown case '+p['id'])
        try: check_source(p['source'],plan_path,workspace)
        except (OSError,ValueError,KeyError,IndexError,TypeError) as exc: fail('code-task',str(exc))
    for impact in impacts.values():
        if not set(impact['codeEvidenceIds'])<=set(evidence): fail('regression',impact['id']+': missing current code evidence')
        if not set(impact['changedFiles'])<=all_modified: fail('regression',impact['id']+': impact is outside the planned changes')
        mapped=[cases[x] for x in impact['testCaseIds'] if x in cases]
        if len(mapped)!=len(impact['testCaseIds']): fail('regression',impact['id']+': unknown test case')
        if impact['decision']=='regression':
            if not impact['changedFiles'] or not mapped or any(x['kind']!='regression' or x['impactId']!=impact['id'] for x in mapped): fail('regression',impact['id']+': direct regression needs changed files and linked regression cases')
        elif impact['decision']=='covered':
            if not mapped or any(x['kind']!='primary' for x in mapped): fail('regression',impact['id']+': covered behavior needs primary cases')
        elif mapped: fail('regression',impact['id']+': unaffected code must not add regression cases')
    for c in cases.values():
        if c['kind']=='regression' and (c['impactId'] not in impacts or c['id'] not in impacts[c['impactId']]['testCaseIds']): fail('regression',c['id']+': missing reciprocal direct impact')
    if not checks['one-to-one']:
        try:
            edges,coverage=derive_route(model,state,atomic)
            if model['edges']!=edges: fail('route','Edges must be exactly the selected route pairs')
            if model['coverage']!=coverage: fail('route','Route must preserve the exact primary route and independently proved minimum')
        except (ValueError,KeyError,TypeError) as exc: fail('route',str(exc))
    if with_views:
        for file,wanted in ((path.with_suffix('.html'),html_text(model,state,plan,atomic)),(plan_path.with_suffix('.md'),md_text(plan,model))):
            if not file.is_file() or file.read_text(encoding='utf-8')!=wanted: fail('views','Missing or stale view '+file.name)
    return result()

def execute(command,path,workspace):
    path=path.resolve();workspace=workspace.resolve();path.relative_to(workspace)
    model=load_json(path);plan_path=path.parent/'task-plan.json'
    if command=='build':
        state=load_json(resolve_file(path,model['stateGraph']['path'],workspace));atomic_path=resolve_file(path,model['atomicGraph']['path'],workspace);atomic=load_json(atomic_path)
        report=evaluate_atomic(atomic,atomic_path,workspace)
        if report['status']!='passed': return report
        model['edges'],model['coverage']=derive_route(model,state,atomic)
        plan=load_json(plan_path);plan['testCases']={'path':os.path.relpath(path,plan_path.parent).replace(os.sep,'/'),'sha256':digest(model)}
        report=evaluate(model,path,workspace,task_plan=plan)
        if report['status']!='passed': return report
        path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        path.with_suffix('.html').write_text(html_text(model,state,plan,atomic),encoding='utf-8');plan_path.with_suffix('.md').write_text(md_text(plan,model),encoding='utf-8')
    return evaluate(model,path,workspace,with_views=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('build','check'));p.add_argument('model',type=Path);p.add_argument('--workspace',type=Path,required=True);args=p.parse_args()
    try: report=execute(args.command,args.model,args.workspace)
    except (OSError,ValueError,KeyError,TypeError,RecursionError,IndexError) as exc: report={'scope':'planning-artifacts-only','status':'failed','error':str(exc)}
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='passed' else 1
if __name__=='__main__': raise SystemExit(main())
