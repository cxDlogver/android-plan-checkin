const fs=require('node:fs'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const {DeviceDriver}=require('./device-driver.cjs'),{snapshot}=require('./p1.cjs'),progress=require('./progress.cjs');
const api=process.argv[2]||'36',startedAt=new Date().toISOString(),directory=`resource/acceptance/runs/${startedAt.replace(/[:.]/g,'-')}/product-flow-api${api}`;
const resume=process.argv[3]==='resume';
const priorCommand=progress.read().commands[`product-flow-${api}`];
const prior=resume&&priorCommand?.record?JSON.parse(fs.readFileSync(priorCommand.record,'utf8')):null;
let context=prior?.context||{name:`原生流程 API${api} ${(prior?.startedAt||startedAt).slice(11,19)}`,planId:null,recordId:null};
const device=new DeviceDriver(api,directory),assertions=[],sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const reusedEvidence=[];
const completed=id=>prior?.assertions.some(item=>item.id===id&&item.status==='PASS');
if(prior){assert.ok(prior.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256));reusedEvidence.push(...prior.evidence);assertions.push(...prior.assertions.filter(item=>item.status==='PASS').map(item=>({...item,reusedFrom:priorCommand.record})));}
const check=(id,expected,actual)=>{const status=JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL';assertions.push({id,expected,actual,status});fs.writeFileSync(`${directory}/assertions.json`,JSON.stringify(assertions,null,2)+'\n');console.log(`${status} ${id}`);assert.equal(status,'PASS',id);};
async function facts(name){device.deepLink('plancheckin-dev://native');await device.waitSource(source=>source.includes('原生模块验证'));await device.clickVisible('native.snapshot');let report;for(let i=0;i<10;i++){report=await device.report();if(report.snapshot)break;await new Promise(resolve=>setTimeout(resolve,300));}assert.ok(report.snapshot);fs.writeFileSync(`${directory}/${name}.json`,JSON.stringify(report.snapshot,null,2)+'\n');return report.snapshot;}
async function today(){device.deepLink('plancheckin-dev://today');return device.waitSource(source=>source.includes('plan.create'));}
async function main(){
  fs.writeFileSync(`${directory}/device.json`,JSON.stringify(device.identity(),null,2)+'\n');
  const state=progress.read();assert.equal(state.commands[`native-device-${api}`]?.status,'PASS','Complete first native module validation before product flow.');
  fs.writeFileSync(`${directory}/build-reference.json`,JSON.stringify({build:state.commands['native-debug'].record,apk:state.commands['native-debug'].artifacts,source:snapshot(['app','src','package.json','pnpm-lock.yaml'])},null,2)+'\n');
  await device.open();device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');await device.waitSource(source=>source.includes('今日'));
  device.deepLink('plancheckin-dev://native');await device.waitSource(source=>source.includes('native.clock.input'));
  await device.input('native.clock.input','2026-10-10T04:00:00.000Z');await device.hideKeyboard();await device.clickVisible('native.clock.apply');
  const name=context.name;
  let created=prior?await facts('resume-before'):null,plan=created?.facts.plans.find(plan=>plan.name===name);
  if(!plan){await today();await device.click('plan.create');await device.waitSource(source=>source.includes('plan.name'));await device.input('plan.name',name);await device.hideKeyboard();await device.clickVisible('plan.weekday.everyday');await device.clickVisible('plan.save');await device.waitSource(source=>source.includes('计划详情')&&source.includes(name));await device.save('created-detail');created=await facts('created-facts');plan=created.facts.plans.find(plan=>plan.name===name);}
  else fs.writeFileSync(`${directory}/created-facts.json`,JSON.stringify(created,null,2)+'\n');
  context.planId=plan.id;
  if(!completed('create.rule')){check('create.committed',true,!!plan);check('create.kind','fixed',plan.type);check('create.rule',127,JSON.parse(created.facts.rule_versions.find(rule=>rule.plan_id===plan.id&&rule.kind==='weekday_mask').value_json).weekdayMask);}
  if(!completed('quick-choice.cancel-no-write')){await today();await device.clickVisible(`today.result.${plan.id}.success`);await device.waitSource(source=>source.includes('确认记录'));await device.save('confirmation-before-save');await device.back();await device.waitSource(source=>source.includes('放弃未保存内容'));await device.text('确认');await device.waitSource(source=>source.includes('plan.create'));const cancelled=await facts('cancelled-facts');check('quick-choice.cancel-no-write',0,cancelled.facts.cycle_records.filter(row=>row.plan_id===plan.id).length);}
  let saved;
  if(completed('submit.note'))saved=JSON.parse(fs.readFileSync(prior.evidence.find(file=>file.path.endsWith('/saved-facts.json')).path,'utf8'));
  else{await today();await device.clickVisible(`today.result.${plan.id}.success`);await device.waitSource(source=>source.includes('record.note'));await device.input('record.note','首次原生提交');await device.hideKeyboard();await device.clickVisible('record.save');await device.waitSource(source=>source.includes('已保存'));await device.save('saved-today');saved=await facts('saved-facts');const record=saved.facts.cycle_records.find(row=>row.plan_id===plan.id);check('submit.one-record',1,saved.facts.cycle_records.filter(row=>row.plan_id===plan.id).length);check('submit.result','success',record.result);check('submit.note','首次原生提交',record.note);}
  const record=saved.facts.cycle_records.find(row=>row.plan_id===plan.id);context.recordId=record.id;
  const alreadyModified=created.facts.cycle_records.find(row=>row.id===record.id&&row.revision===2&&row.result==='failure'&&row.note==='当天原生修正');
  if(!alreadyModified){await today();await device.clickVisible(`record.open.${plan.id}`);await device.waitSource(source=>source.includes('查看或修改记录'));await device.clickVisible('record.result.failure');await device.input('record.note','当天原生修正');await device.hideKeyboard();await device.clickVisible('record.save');await device.waitSource(source=>source.includes('plan.create'));}
  const modified=await facts('modified-facts'),actual=modified.facts.cycle_records.find(row=>row.id===record.id),original=modified.facts.cycle_record_originals.find(row=>row.record_id===record.id);check('modify.result','failure',actual.result);check('modify.revision',2,actual.revision);check('modify.original',{result:'success',note:'首次原生提交'},{result:original.original_result,note:original.original_note});
  await today();await device.click('tab.calendar');await device.waitSource(source=>source.includes('日历'));await device.save('calendar');await device.click('tab.plans');await device.waitSource(source=>source.includes(name));await device.save('plans');
}
main().catch(async error=>{assertions.push({id:'execution',expected:'complete product flow',actual:error.message,status:'FAIL'});console.error(error.message);try{if(device.sessionId)await device.save('failure');}catch{}process.exitCode=1;}).finally(async()=>{
  try{await device.close();}catch(error){console.error(error.message);process.exitCode=1;}
  const evidence=[...reusedEvidence,...fs.readdirSync(directory).filter(file=>file!=='assertions.json').map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))];
  const status=assertions.some(item=>item.status==='FAIL')?'FAIL':'PASS',result={status,api:Number(api),startedAt,endedAt:new Date().toISOString(),previousRecord:priorCommand?.record||null,context,scope:'native create / cancel quick choice / submit / modify-original / tabs smoke; full BDD cases remain separate',assertions,evidence};
  fs.writeFileSync(`${directory}/assertions.json`,JSON.stringify(assertions,null,2)+'\n');fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');fs.writeFileSync(`${directory}/evidence-manifest.json`,JSON.stringify([...evidence,...['assertions.json','result.json'].map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))],null,2)+'\n');
  progress.update(state=>{state.commands[`product-flow-${api}`]={status,record:`${directory}/result.json`};for(const id of ['IP18','IP20','IP21','IP25'])state.tasks.find(task=>task.id===id).evidence.push(`${directory}/result.json`);});console.log(`${status}: ${directory}/result.json`);
});
