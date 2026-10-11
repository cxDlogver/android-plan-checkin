const fs=require('node:fs');
const assert=require('node:assert/strict');
const {sha,snapshot}=require('./p1.cjs');
const {createRun}=require('./evidence-run.cjs');
const {VerificationClient}=require('./verification-bridge.cjs');
const {DeviceDriver}=require('./device-driver.cjs');
const progress=require('./progress.cjs');
const api=process.argv[2]||'36',rows=process.argv.slice(3);
const names=rows.length?rows:['cycle_unique','once_unique','cross_plan_due','missing_due','actual_mismatch','enum','serial_snapshot','cas'];
assert.ok(names.every(name=>['cycle_unique','once_unique','cross_plan_due','missing_due','actual_mismatch','enum','serial_snapshot','cas'].includes(name)));
const client=new VerificationClient(api),configId=`api${api}-393dp-font1`;
const launch=new DeviceDriver(api,'.cache/verification-bridge/launch');
const source=snapshot(['src/verification/sql-cases-development.ts','src/infrastructure/database','scripts/native-sql-cases.cjs']);
function revision(facts){return Number(facts.app_meta.find(row=>row.key==='data_revision').value);}
async function main(){
  launch.identity();
  await launch.open();
  launch.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');
  await launch.waitSource(source=>source.includes('今日'),120000);
  launch.deepLink('plancheckin-dev://native');
  await launch.waitSource(source=>source.includes('原生模块验证'),90000);
  await client.waitReady();
  const ready=await client.status();assert.ok(ready.hello.capabilities?.includes('sqlCase'),'Reload the development bundle with the SQL case capability.');
  await client.call('clock',{instant:'2026-10-11T04:00:00Z'});
  await client.call('fixture',{name:'F01',zone:'Asia/Shanghai',confirm:'RESET_ISOLATED_DEV_DATABASE'});
  for(const name of names){
    const caseId=name==='serial_snapshot'?'AC010':name==='cas'?'AC119':'AC007',rowId=caseId==='AC007'?name:'default',ip=caseId==='AC007'?'IP07':'IP08';
    const run=createRun(`${caseId}-${rowId}-${configId}`,{api,name,source},[ip],{caseId,rowId,configId,fr:caseId==='AC007'?['FR10','FR11','FR13','FR29','FR32']:['FR10','FR11','FR16','FR32'],at:['AT24']});
    if(!run)continue;
    let error=null;
    try{
      run.write('device.json',launch.identity());run.write('bridge-identity.json',await client.status());
      const response=await client.call('sqlCase',{name}),data=response.observation;run.write('native-observation.json',response);
      run.check('native-context-preserved',ready.hello.contextId,response.contextId);
      if(caseId==='AC007'){
        run.check('AC007.A1.rejected',true,data.attempts.every(attempt=>/constraint|UNIQUE|FOREIGN KEY|CHECK/i.test(attempt.failure||'')));
        run.check('AC007.A1.counts',Object.fromEntries(Object.entries(data.before).map(([table,rows])=>[table,rows.length])),Object.fromEntries(Object.entries(data.after).map(([table,rows])=>[table,rows.length])));
        run.check('AC007.A1.foreignKeys',[],data.foreignKeyCheck);
        if(['cross_plan_due','missing_due'].includes(name))run.check('AC007.A2.deferred-commit-rejected','commit',data.attempts[0].stage);
        run.check('AC007.A2.deferred-schema',true,/ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED/.test(data.schema.find(row=>row.name==='one_time_results').sql));
        run.check('AC007.A3.logical-facts',true,data.attempts.every(attempt=>attempt.afterSha256===data.beforeSha256&&attempt.foreignKeyCheck.length===0));
        if(name==='enum')run.check('AC007.enum.both-constraints',['unknown_result','illegal_weekly_target'],data.attempts.map(attempt=>attempt.label));
      } else if(caseId==='AC010'){
        const plan=data.before.plans.find(row=>row.type==='fixed');
        const firstStart=data.order.indexOf('first-start'),firstCommit=data.order.indexOf('first-before-commit'),readStart=data.order.indexOf('read-start'),readEnd=data.order.indexOf('read-end'),lastStart=data.order.indexOf('last-start');
        run.check('AC010.A1.serial-order',true,firstStart<firstCommit&&firstCommit<readStart&&readStart<readEnd&&readEnd<lastStart);
        run.check('AC010.A1.transaction-context-rejected',true,data.escapedRejected);
        run.check('AC010.A2.no-success-before-commit',false,data.beforeCommitNotification);
        run.check('AC010.A2.failed-transaction-no-revision',data.failedBeforeSha256,data.failedAfterSha256);
        run.check('AC010.A3.read-plan-count',data.before.plans.length,data.observations[0].plans);
        run.check('AC010.A3.read-complete-revision',plan.revision+1,data.observations[2].revision);
        run.check('AC010.A3.read-data-revision',String(revision(data.before)+1),data.observations[1].dataRevision);
        run.check('AC010.A3.next-write-plan-revision',plan.revision+2,data.after.plans.find(row=>row.id===plan.id).revision);
        run.check('AC010.A3.next-write-data-revision',revision(data.before)+2,revision(data.after));
      } else {
        const before=data.before.plans.find(row=>row.id===data.planId),after=data.after.plans.find(row=>row.id===data.planId);
        run.check('AC119.A1.successful-CAS',1,data.firstChanges);
        run.check('AC119.A1.plan-revision',before.revision+1,after.revision);
        run.check('AC119.A1.data-revision',revision(data.before)+1,revision(data.after));
        run.check('AC119.A2.stale-CAS',0,data.staleChanges);
        run.check('AC119.A2.rollback',true,data.rolledBack);
        run.check('AC119.A2.rollback-facts',data.committed,data.after);
        run.check('AC119.A3.cancelled-version-included',3,data.nextRevision);
        run.check('AC119.A3.same-instant',true,data.after.rule_versions.filter(row=>row.plan_id===data.planId&&row.kind==='weekday_mask').every(row=>row.created_at_ms===before.created_at_ms));
      }
    }catch(failure){error=failure;console.error(`${name}: ${failure.message}`);}
    run.finish(error,[...(caseId==='AC010'?['Connection count is additionally established by the single-open source audit; this report exercises the real one-executor transaction queue.','DTO projections remain separate AC116']:caseId==='AC119'?['Primitive SQL only; production command revision/reconcile remains separate AC104']:[]),'Parent acceptance remains incomplete until both APIs and all required scopes are linked.']);
    if(error)break;
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;}).finally(async()=>{try{await client.call('fault',{point:null});await client.call('clock',{instant:null});}catch{}try{await launch.close();}catch{}});
