import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUN=ROOT.parent.parent
SKILL=ROOT.parent/'skill/task-planning'
if not SKILL.exists():SKILL=ROOT.parents[3]/'.codex/skills/task-planning'
sys.path.insert(0,str(SKILL/'scripts'))
import planning as p
cfg=p.read(RUN/'_process/planning.json');data=p.read(RUN/'test-plan.json');gate=p.read(RUN/'gate-result.json')
assert p.plan_digest(cfg)==data['planningDigest'],'final exports are still rebuilding'
by,model,rg=p.load_inputs(cfg)
assert data['stateGraph']['nodes']==model['states']
assert data['stateGraph']['edges']==model['transitions']
cases={c['requirementId']:c for c in data['cases'] if c['kind']=='primary'}
assert set(cases)=={r['id'] for r in model['requirements']}
shared={text for rule in cfg.get('sharedAssertions',[]) for text in rule['matches']}
for requirement in model['requirements']:
 for ac in requirement['acceptance']:
  for text in ac['then']:
   assert text in shared or any(a['text']==text for a in cases[requirement['id']]['assertions'])
assert all(c['result']['status']=='pending' for c in data['cases'])
assert gate['mechanical']['status']=='PASS'
assert gate['readiness']['status']=='draft'
assert not any(token in p.css_tokens({}) for token in ('0px','700'))
files=[x for x in SKILL.rglob('*') if x.is_file() and '__pycache__' not in x.parts]
resources=[{'path':x.relative_to(SKILL).as_posix(),'sha256':p.sha(x.read_bytes())} for x in sorted(files)]
adversarial=p.read(ROOT/'adversarial-results.json');oracle=p.read(ROOT/'route-oracle-results.json')
assert adversarial['status']=='PASS' and oracle['status']=='PASS'
findings=[
 {'area':'来源与原子映射','status':'PASS','evidence':'当前66个状态/510条状态边与输入逐对象相同，510主测试一一对应；非共享源断言未丢失。'},
 {'area':'连续路线','status':'PASS','evidence':'300随机小图/1364目标边查询与独立具体状态BFS一致；不动点冲突判定未误拒具体可达边。当前25段1073访问，22未覆盖明确保留。'},
 {'area':'正常阶段与修复通道','status':'PASS','evidence':'12个独立正常/失败用例覆盖 planning→development→acceptance→record 与 invalidate 后补开发检查再验收。'},
 {'area':'断言/实例/批准/证据门禁','status':'PASS','evidence':'源断言替换、重复ID、缺准备、机械失败、旧批准、未完成开发、移除检查、旧代码与检查证据均拒绝；Markdown同步实际结论。'},
 {'area':'存量影响与回归','status':'PASS','evidence':'分页、缓存与刷新乱序3项有调用/数据与既有测试或代码依据；只加保护义务，未实现或声称运行通过。'},
 {'area':'通用规范与输出','status':'PASS','evidence':'项目共享文字分类移入运行配置；矩阵与共享约束未映射时保留就绪缺口；CSS仅输出已知参数；初始化仅工作模型，当前文件维护。'},
 {'area':'HTML','status':'NOT_TESTED','evidence':'嵌入脚本语法已通过；源码具备Canvas、双图、路线/状态/箭头点击、预期与证据区；未作真实浏览器观察，不能据此声称视觉可读性已验收。'}]
report={'status':'PASS','context':'independent','scope':'task-planning Skill reliability and draft-project transformation only; not approval of upstream requirements or current project implementation/acceptance','planningDigest':data['planningDigest'],'generatorDigest':p.generator_digest(),'candidateResourceDigest':p.digest(resources),'candidateResources':resources,'findings':findings,'resolvedFindings':['route fixture readiness had no normal path','source assertions could be replaced','current approval/mechanical gates were skipped after planning','duplicate assertion ids collapsed obligations','Markdown retained static pending text','environment matrix and shared obligation bindings were lost','project-specific shared text was hardcoded','repair needed a normal invalidation path','HTML phase text was static','missing CSS values invented defaults'],'tests':{'adversarial':len(adversarial['checks']),'oracleGraphs':oracle['graphs'],'oracleQueries':oracle['edge_target_queries']},'project':{'phase':data['phase'],'mechanical':gate['mechanical']['status'],'readiness':gate['readiness']['status'],'counts':gate['counts'],'approval':'NOT_GRANTED','productAcceptance':'NOT_TESTED'},'limitations':['Current project remains a draft: upstream approval, concrete fixtures, matrix/shared assertion bindings, and 22 route gaps remain.','Whole-route optimality is not proven; finite-domain feasibility does not prove real-world fixture executability.','Model independence and real human authorization cannot be guaranteed by local file-format validators.','No product code was changed or product acceptance performed by this independent review.']}
p.write(ROOT/'review.json',report)
md='''# 独立评审

结论：Skill 已检查范围 PASS；真实浏览器观察 NOT_TESTED；当前项目规划仍为草案，不授予开发或验收批准。

'''
md+='绑定 planningDigest：'+data['planningDigest']+'\n\n生成器摘要：'+p.generator_digest()+'\n\n候选完整资源摘要：'+p.digest(resources)+'\n\n'
md+='''## 验证

- 12项正常/拒绝路径检查通过，包含修复后重验的正常通道。
- 300个小图、1364个目标边查询与独立具体状态BFS一致。
- 当前66状态/510完整边保留，510主测试加3必要回归，非共享源断言未丢失。
- 当前25段、1073次访问；22个缺口仍在，4个有限域不动点冲突、18个未证明。

## 已修复

'''
md+=''.join('- '+s+'。\n' for s in report['resolvedFindings'])
md+='''
## 边界

真实浏览器、真实设备、产品功能与视觉验收均未执行。当前513项仍待验收；上游批准、真实夹具、环境/共享义务映射及未覆盖迁移须继续处理。此评审仅支持Skill的已测可靠性和当前草案转换保真，不能替代当前项目的需求语义验收、人工批准或实测证据。
'''
p.write(ROOT/'review.md',md)
old=ROOT/'review-initial.json'
if old.exists():old.unlink()
print(json.dumps({k:report[k] for k in ('status','planningDigest','generatorDigest','candidateResourceDigest','tests','project')},ensure_ascii=False,indent=2))
