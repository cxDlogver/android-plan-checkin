const fs=require('node:fs');
const path=require('node:path');
const {sha}=require('./p1.cjs');
const progress=require('./progress.cjs');
function report(caseId,implementationId,assertions,paths,limitations=[]){
  const template=JSON.parse(fs.readFileSync('resource/acceptance/单实例报告模板.json','utf8'));
  const runId=`${new Date().toISOString().replace(/[:.]/g,'-')}-${caseId.toLowerCase()}`;
  const directory=`resource/acceptance/runs/${runId}/${caseId}/default/windows-build`;
  fs.mkdirSync(directory,{recursive:true});
  const evidence=paths.filter(file=>fs.existsSync(file)).map(file=>({profile:'E-BUILD',path:file,sha256:sha(fs.readFileSync(file))}));
  const status=assertions.every(assertion=>assertion.status==='PASS')?'PASS':'FAIL';
  fs.writeFileSync(`${directory}/assertions.json`,JSON.stringify(assertions,null,2)+'\n');
  const result={...template,status,runId,caseId,rowId:'default',configId:'windows-build',implementationIds:[implementationId],fr:caseId==='AC001'?['FR32']:['FR30','FR32'],at:caseId==='AC001'?['AT28']:['AT27','AT28'],source:{snapshotSha256:sha(JSON.stringify(require('./p1.cjs').snapshot(['app','src','plugins','assets','package.json','pnpm-lock.yaml']))),lockfileSha256:sha(fs.readFileSync('pnpm-lock.yaml'))},startedAt:new Date().toISOString(),endedAt:new Date().toISOString(),steps:paths.map(file=>({evidence:file})),assertions,evidence,limitations};
  fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
  fs.writeFileSync(`${directory}/evidence-manifest.json`,JSON.stringify([...evidence,...['assertions.json','result.json'].map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))],null,2)+'\n');
  progress.update(state=>{state.acceptance[caseId]={status,report:`${directory}/result.json`};const task=state.tasks.find(task=>task.id===implementationId);task.status=status==='PASS'?'DONE':'IN_PROGRESS';task.completedAt=status==='PASS'?new Date().toISOString():null;task.evidence.push(`${directory}/result.json`);if(status==='PASS'){const definition=JSON.parse(fs.readFileSync('resource/acceptance/追踪目录.json','utf8')).tasks.find(item=>item.id===implementationId);task.workDone=[...definition.work.map((_,i)=>`W${i+1}`),...definition.output.map((_,i)=>`D${i+1}`),'V1','V2'];}});
  if(status==='PASS'){
    for(const file of ['resource/acceptance/scenarios/01-工程准入.md','resource/BDD验收-checklist-计划打卡-Android-v1.md']){let text=fs.readFileSync(file,'utf8');text=text.replace(new RegExp(`- \\[ \\] (\\[${caseId}｜[^\\n]+)`),'- [x] $1');text=text.replace(`- [ ] ${caseId} — 场景/全部参数/配置完成（当前NOT_RUN）。`,`- [x] ${caseId} — 本项Windows范围PASS，[执行报告](${path.relative(path.dirname(file),`${directory}/result.json`).replaceAll('\\','/')})。`);for(const assertion of assertions)text=text.replace(`- [ ] ${assertion.id} —`,`- [x] ${assertion.id} —`);text=text.replace(`- [ ] ${caseId}.E0 —`,`- [x] ${caseId}.E0 —`).replace(`- [ ] ${caseId}.E1 —`,`- [x] ${caseId}.E1 —`);fs.writeFileSync(file,text);}
  }
  console.log(`${status} ${caseId}: ${directory}/result.json`);return result;
}
function check(id,expected,actual){return {id,expected,actual,status:JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL'};}
module.exports={report,check};
