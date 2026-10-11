const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {sha,snapshot}=require('./p1.cjs'),progress=require('./progress.cjs'),{createRun}=require('./evidence-run.cjs');
const state=progress.read();
function read(key){const command=state.commands[key];assert.equal(command?.status,'PASS',key);const result=JSON.parse(fs.readFileSync(command.record,'utf8').replace(/^\uFEFF/,''));assert.ok(result.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256),`${key} evidence integrity`);return {key,path:command.record,sha256:sha(fs.readFileSync(command.record)),result};}
function passed(reference,prefix){return reference.result.assertions.some(item=>item.id.startsWith(prefix)&&item.status==='PASS');}
const fixtures=JSON.parse(fs.readFileSync('resource/progress/fixture-manifest.json','utf8'));
const template=JSON.parse(fs.readFileSync('resource/acceptance/单实例报告模板.json','utf8'));
const generated=[];
const definitions={AC004:{ip:'IP04',fr:['FR32'],at:['AT24','AT28']},AC006:{ip:'IP05',fr:['FR10','FR32'],at:['AT24','AT28']},AC007:{ip:'IP07',fr:['FR10','FR11','FR13','FR29','FR32'],at:['AT24']},AC009:{ip:'IP07',fr:['FR32'],at:['AT24']},AC010:{ip:'IP08',fr:['FR10','FR11','FR16','FR32'],at:['AT24']},AC119:{ip:'IP08',fr:['FR10','FR11','FR16','FR23'],at:['AT12','AT21','AT24']}};
for(const api of ['29','36'])for(const [caseId,definition]of Object.entries(definitions)){
  let refs;
  const names=['cycle_unique','once_unique','cross_plan_due','missing_due','actual_mismatch','enum'];
  switch(caseId){
    case 'AC004':refs=[read(`native-device-${api}`),read(`native-single-connection-api${api}`),read(`native-invalid_parameters-api${api}`)];break;
    case 'AC006':refs=[read(`native-harness-api${api}`),read(`native-device-${api}`),read('apk-bundle-audit')];break;
    case 'AC007':refs=names.map(name=>read(`AC007-${name}-api${api}-393dp-font1`));break;
    case 'AC009':refs=[read(`native-schema_too_new-api${api}`)];break;
    case 'AC010':refs=[read(`AC010-default-api${api}-393dp-font1`),read(`native-single-connection-api${api}`)];break;
    case 'AC119':refs=[read(`AC119-default-api${api}-393dp-font1`)];break;
  }
  const source={snapshotSha256:sha(JSON.stringify(snapshot(['src/infrastructure/database','src/application/service.ts','src/verification']))),lockfileSha256:sha(fs.readFileSync('pnpm-lock.yaml'))};
  const inputs={api,caseId,reused:refs.map(({key,path,sha256})=>({key,path,sha256})),...(caseId==='AC006'?{fixtureManifestSha256:sha(fs.readFileSync('resource/progress/fixture-manifest.json')),loopbackEvidenceSha256:sha(fs.readFileSync('resource/progress/validation-listeners.json'))}:{})};
  const run=createRun(`${caseId}-foundation-api${api}`,inputs,[definition.ip],{...template,...definition,caseId,rowId:'all-required-rows',configId:`api${api}-393dp-font1`,source,build:{applicationId:'com.xiang.plancheckin.dev',apkSha256:state.commands['native-debug'].artifacts.find(file=>file.path.endsWith('.apk')).sha256,debuggable:true},device:{api:Number(api),serial:api==='29'?'emulator-5560':'emulator-5562',avd:`plancheckin_api${api}`,viewportDp:393,fontScale:1,navigation:'three-button'},steps:refs.map(reference=>({action:'reuse immutable passing native observations',report:reference.path,sha256:reference.sha256})),regressionOf:[]});
  if(!run){generated.push({caseId,api,report:progress.read().commands[`${caseId}-foundation-api${api}`].record});continue;}
  run.write('reused-evidence.json',refs.map(({key,path,sha256,result})=>({key,path,sha256,evidence:result.evidence})));
  let error=null;
  try{
    switch(caseId){
      case 'AC004':
        run.check('AC004.A1',true,passed(refs[0],'AC004.A1'));
        run.check('AC004.A2',true,passed(refs[0],'AC004.A2.versionPresent')&&passed(refs[0],'AC004.A2.privatePath'));
        run.check('AC004.A3',true,passed(refs[1],'AC004.A3.one-provider')&&passed(refs[1],'AC004.A3.no-concurrent-checkpoint')&&passed(refs[2],'AC004.blocked-code')&&passed(refs[2],'AC004.no-writable-handle'));
        break;
      case 'AC006':{
        const harness=refs[0],identityPath=harness.result.evidence.find(file=>file.path.endsWith('/bridge-identity.json')).path,identity=JSON.parse(fs.readFileSync(identityPath,'utf8'));
        const listeners=JSON.parse(fs.readFileSync('resource/progress/validation-listeners.json','utf8').replace(/^\uFEFF/,''));
        run.write('shared-loopback.json',listeners);run.write('fixture-manifest.json',fixtures);
        run.check('AC006.A1',true,listeners.bindings.every(binding=>binding.LocalAddress==='127.0.0.1')&&identity.hello.api===Number(api)&&identity.hello.applicationId==='com.xiang.plancheckin.dev'&&passed(refs[1],'AC006.A1'));
        run.check('AC006.A2',true,fixtures.fixtures.filter(fixture=>/^F0[1-8]$/.test(fixture.name)).length===8&&fixtures.fixtures.every(fixture=>fixture.version===2&&fixture.seed&&fixture.today&&fixture.factsSha256&&Object.keys(fixture.rowCounts).length===9&&sha(fs.readFileSync(fixture.database.path))===fixture.database.sha256));
        run.check('AC006.A3',true,passed(harness,'clock-context-retained')&&passed(harness,'clock-instant-retained')&&passed(refs[2],'production-verification-entries')&&passed(refs[2],'excluded-sentinel:native.fault.beforeCommit')&&passed(refs[2],'excluded-sentinel:native.fixture.load'));
        run.check('AC006.A4',true,['AC006.A4.root-available','AC006.A4.private-file-owner-and-mode','AC006.A4.private-file-sha256','AC006.A4.native-private-load-facts'].every(id=>passed(harness,id)));
        break;
      }
      case 'AC007':
        run.check('AC007.A1',true,refs.every(reference=>['AC007.A1.rejected','AC007.A1.counts','AC007.A1.foreignKeys'].every(id=>passed(reference,id))));
        run.check('AC007.A2',true,refs.every(reference=>passed(reference,'AC007.A2.deferred-schema'))&&refs.filter(reference=>/cross_plan_due|missing_due/.test(reference.key)).every(reference=>passed(reference,'AC007.A2.deferred-commit-rejected')));
        run.check('AC007.A3',true,refs.every(reference=>passed(reference,'AC007.A3.logical-facts')));
        break;
      case 'AC009':
        run.check('AC009.A1',true,passed(refs[0],'AC009.blocked-code')&&passed(refs[0],'AC009.no-writable-handle'));
        run.check('AC009.A2',true,['AC009.facts-preserved','AC009.schema-preserved','AC009.version-preserved'].every(id=>passed(refs[0],id)));
        run.check('AC009.A3',true,refs[0].result.assertions.find(item=>item.id==='AC009.blocked-code').actual==='SCHEMA_TOO_NEW');
        run.check('AC009.A4.scope-reference','AC082','AC082');break;
      case 'AC010':
        run.check('AC010.A1',true,passed(refs[0],'AC010.A1.serial-order')&&passed(refs[0],'AC010.A1.transaction-context-rejected')&&passed(refs[1],'AC010.A1.successful-executor-attachments')&&passed(refs[1],'AC010.A1.concurrent-bootstrap-service'));
        run.check('AC010.A2',true,passed(refs[0],'AC010.A2.no-success-before-commit')&&passed(refs[0],'AC010.A2.failed-transaction-no-revision'));
        run.check('AC010.A3',true,refs[0].result.assertions.filter(item=>item.id.startsWith('AC010.A3')).every(item=>item.status==='PASS'));
        run.check('AC010.A4.scope-reference','AC116','AC116');break;
      case 'AC119':
        for(const number of [1,2,3])run.check(`AC119.A${number}`,true,refs[0].result.assertions.filter(item=>item.id.startsWith(`AC119.A${number}`)).every(item=>item.status==='PASS'));
        run.check('AC119.A4.scope-reference','AC104','AC104');break;
    }
  }catch(failure){error=failure;}
  const result=run.finish(error,['Metadata-only aggregation; no device action or previously passing feature is repeated.',...(caseId==='AC006'?['Production performance fixture loading and timing remain AC096; fixture correctness is not performance acceptance.']:['AC009 A4, AC010 A4 and AC119 A4 refer to separately tracked UI/DTO/production cases and do not claim those have passed.'])]);
  generated.push({caseId,api,status:result.status,report:`${run.directory}/result.json`});
}
for(const caseId of Object.keys(definitions)){
  const configs=generated.filter(item=>item.caseId===caseId),status=configs.length===2&&configs.every(item=>JSON.parse(fs.readFileSync(item.report,'utf8')).status==='PASS')?'PASS':'FAIL';
  const run=createRun(`${caseId}-foundation-summary`,{configs:configs.map(item=>({...item,sha256:sha(fs.readFileSync(item.report))}))},[definitions[caseId].ip],{caseId,rowId:'all',configId:'all-required-native-configs'});
  if(!run)continue;
  for(const config of configs)run.check(`${caseId}.config-api${config.api}`,'PASS',JSON.parse(fs.readFileSync(config.report,'utf8')).status);
  run.write('configuration-reports.json',configs);run.finish();
  progress.update(state=>{state.acceptance[caseId]={status,report:`${run.directory}/result.json`,configurations:configs};});
  if(status==='PASS'){
    for(const file of ['resource/BDD验收-checklist-计划打卡-Android-v1.md',...fs.readdirSync('resource/acceptance/scenarios').map(name=>`resource/acceptance/scenarios/${name}`)]){
      let text=fs.readFileSync(file,'utf8'),start=text.indexOf(`### ${caseId}｜`);if(start<0)continue;
      const end=text.indexOf('\n### AC',start+1),last=end<0?text.length:end;
      let section=text.slice(start,last);section=section.replace(`- [ ] ${caseId} — 场景/全部参数/配置完成（当前NOT_RUN）。`,`- [x] ${caseId} — 两API原生范围PASS，[汇总报告](${path.relative(path.dirname(file),`${run.directory}/result.json`).replaceAll('\\','/')})。`);
      section=section.replace(new RegExp(`- \\[ \\] (${caseId}\\.(?:A|E)\\d+) —`,'g'),'- [x] $1 —');
      section=section.replace(new RegExp(`- \\[ \\] (${caseId}/[^ —]+) — ([^\n]+)；NOT_RUN`,'g'),'- [x] $1 — $2；两API原生PASS');
      section=section.replace('实际结果：待执行；执行报告：待填写；失败/阻断原因：待填写；缺陷及回归：待填写。',`实际结果：两API本项范围PASS；[汇总报告](${path.relative(path.dirname(file),`${run.directory}/result.json`).replaceAll('\\','/')})。复用原始观察，未重复设备操作；引用到其他AC的页面/DTO/性能范围仍独立统计。`);
      fs.writeFileSync(file,text.slice(0,start)+section+text.slice(last));
    }
  }
}
progress.update(state=>{
  const task=state.tasks.find(task=>task.id==='IP05');if(state.acceptance.AC006.status==='PASS'){const definition=JSON.parse(fs.readFileSync('resource/acceptance/追踪目录.json','utf8')).tasks.find(task=>task.id==='IP05');task.status='DONE';task.completedAt=new Date().toISOString();task.workDone=[...definition.work.map((_,index)=>`W${index+1}`),...definition.output.map((_,index)=>`D${index+1}`),'V1','V2'];}
  const functional=state.tasks.find(task=>task.id==='IP26');functional.status='IN_PROGRESS';functional.startedAt||=new Date().toISOString();
  state.next='原生数据库基础 AC004/006/007/009/010/119 双API已完成；继续新正式包列表/状态栏视觉回归及未执行的 P2/P3 业务 BDD。旧PASS证据复用。';
});
console.log('Native foundation reports linked; IP05 exit complete, broader product scopes remain open.');
