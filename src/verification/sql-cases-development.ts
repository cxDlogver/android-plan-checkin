import * as Crypto from 'expo-crypto';
import type { Facts } from '../domain/model';
import { canonical } from '../domain/commands';
import { loadFacts, persist, Tx } from '../infrastructure/database/executor';
import { verificationExecutor } from './runtime-development';

export const sqlCaseNames=['cycle_unique','once_unique','cross_plan_due','missing_due','actual_mismatch','enum','serial_snapshot','cas','cascade'] as const;
type SqlCaseName=typeof sqlCaseNames[number];
const id=()=>Crypto.randomUUID();
const digest=(facts:Facts)=>Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256,canonical(facts));
async function info(tx:Tx){return {version:await tx.first('SELECT sqlite_version() AS version,sqlite_source_id() AS sourceId'),schema:await tx.all("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"),foreignKeyCheck:await tx.all('PRAGMA foreign_key_check')};}

async function constraints(name:SqlCaseName){
  const executor=verificationExecutor();
  return executor.queue(async tx=>{
    const original=await loadFacts(tx);
    try {
      const plan=original.plans.find(row=>row.type==='fixed'),once=original.plans.find(row=>row.type==='one_time');
      if(!plan||!once)throw new Error('F01_REQUIRED');
      const due=original.rule_versions.find(row=>row.plan_id===once.id&&row.kind==='due_on');
      if(!due)throw new Error('DUE_RULE_REQUIRED');
      const cycleId=id(),resultId=id(),otherId=id(),otherDue=id(),today=plan.starts_on,instant=plan.created_at_ms;
      await executor.transaction(tx,async()=>{
        await tx.run('INSERT INTO cycle_records(id,plan_id,business_on,result,note,entry_kind,submitted_at_ms,revision) VALUES(?,?,?,?,?,?,?,1)',[cycleId,plan.id,today,'success','约束验收原值','ordinary',instant]);
        await tx.run('INSERT INTO one_time_results(id,plan_id,business_on,outcome,actual_completed_on,due_rule_version_id,note,entry_kind,submitted_at_ms,revision) VALUES(?,?,?,?,?,?,?,?,?,1)',[resultId,once.id,today,'completed',today,due.id,'约束验收原值','ordinary',instant]);
        await tx.run('INSERT INTO plans(id,type,direction,name,description,created_at_ms,created_on,starts_on,revision) VALUES(?,?,?,?,?,?,?,?,1)',[otherId,'one_time','do','复合外键另一任务','',instant,today,today]);
        await tx.run('INSERT INTO rule_versions(id,plan_id,kind,effective_on,revision,value_json,created_at_ms) VALUES(?,?,?,?,1,?,?)',[otherDue,otherId,'due_on',today,due.value_json,instant]);
      });
      const before=await loadFacts(tx),attempts=[];
      const cycle=(result:string,on=today)=>tx.run('INSERT INTO cycle_records(id,plan_id,business_on,result,note,entry_kind,submitted_at_ms,revision) VALUES(?,?,?,?,?,?,?,1)',[id(),plan.id,on,result,'违规写入','ordinary',instant]);
      const onceResult=(target:string,dueId:string,actual=today)=>tx.run('INSERT INTO one_time_results(id,plan_id,business_on,outcome,actual_completed_on,due_rule_version_id,note,entry_kind,submitted_at_ms,revision) VALUES(?,?,?,?,?,?,?,?,?,1)',[id(),target,today,'completed',actual,dueId,'违规写入','ordinary',instant]);
      const operations=name==='enum'?[
        {label:'unknown_result',run:()=>cycle('unknown','2099-01-01')},
        {label:'illegal_weekly_target',run:()=>tx.run('INSERT INTO rule_versions(id,plan_id,kind,effective_on,revision,value_json,created_at_ms) VALUES(?,?,?,?,1,?,?)',[id(),plan.id,'weekly_target',today,'{"weeklyTarget":8}',instant])},
      ]:[{label:name,run:()=>{
        switch(name){
          case 'cycle_unique':return cycle('success');
          case 'once_unique':return onceResult(once.id,due.id);
          case 'cross_plan_due':return onceResult(otherId,due.id);
          case 'missing_due':return onceResult(otherId,id());
          case 'actual_mismatch':return onceResult(otherId,otherDue,'2099-01-01');
          default:throw new Error('UNSUPPORTED_CONSTRAINT_CASE');
        }
      }}];
      for(const operation of operations){
        let stage='statement',failure:string|null=null;
        try{await executor.transaction(tx,async()=>{await operation.run();stage='commit';});}
        catch(error){failure=String(error);}
        attempts.push({label:operation.label,failure,stage,afterSha256:await digest(await loadFacts(tx)),foreignKeyCheck:await tx.all('PRAGMA foreign_key_check')});
      }
      return {caseId:'AC007',rowId:name,before,after:await loadFacts(tx),beforeSha256:await digest(before),attempts,...await info(tx)};
    } finally {await executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),original));}
  });
}

async function serialSnapshot(){
  const executor=verificationExecutor(),order:string[]=[],observations:unknown[]=[];
  let release:()=>void=()=>{},entered:()=>void=()=>{};
  const gate=new Promise<void>(resolve=>{release=resolve;}),started=new Promise<void>(resolve=>{entered=resolve;});
  let escaped:Tx|undefined;
  const before=await executor.queue(loadFacts);
  const plan=before.plans.find(row=>row.type==='fixed');if(!plan)throw new Error('F01_REQUIRED');
  try {
    let notified=false;
    const first=executor.queue(tx=>executor.transaction(tx,async()=>{
      escaped=tx;order.push('first-start');
      await tx.run('UPDATE plans SET revision=revision+1 WHERE id=?',[plan.id]);
      await tx.run("UPDATE app_meta SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT) WHERE key='data_revision'");
      entered();await gate;order.push('first-before-commit');
    })).then(()=>{notified=true;order.push('first-success');});
    await started;
    const beforeCommitNotification=notified;
    const read=executor.queue(tx=>executor.transaction(tx,async()=>{
      order.push('read-start');observations.push(await tx.first('SELECT count(*) AS plans,sum(revision) AS revisions FROM plans'));
      await new Promise(resolve=>setTimeout(resolve,30));
      observations.push(await tx.first("SELECT value AS dataRevision FROM app_meta WHERE key='data_revision'"));
      observations.push(await tx.first<{revision:number}>('SELECT revision FROM plans WHERE id=?',[plan.id]));
      order.push('read-end');
    },true));
    const last=executor.queue(tx=>executor.transaction(tx,async()=>{
      order.push('last-start');await tx.run('UPDATE plans SET revision=revision+1 WHERE id=?',[plan.id]);
      await tx.run("UPDATE app_meta SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT) WHERE key='data_revision'");
      order.push('last-before-commit');
    }));
    release();await Promise.all([first,read,last]);
    let escapedRejected=false;try{await escaped!.first('SELECT 1');}catch{escapedRejected=true;}
    const after=await executor.queue(loadFacts);
    const failedBefore=await digest(after);
    let failure:string|null=null;
    try{await executor.queue(tx=>executor.transaction(tx,async()=>{await tx.run('UPDATE plans SET revision=revision+1 WHERE id=?',[plan.id]);throw new Error('ROLLBACK_PROBE');}));}catch(error){failure=String(error);}
    const failedAfter=await executor.queue(loadFacts);
    return {caseId:'AC010',rowId:'default',before,after,order,observations,beforeCommitNotification,escapedRejected,failure,failedBeforeSha256:failedBefore,failedAfterSha256:await digest(failedAfter)};
  } finally {release();await executor.queue(tx=>executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),before)));}
}

async function cas(){
  const executor=verificationExecutor();
  return executor.queue(async tx=>{
    const before=await loadFacts(tx),plan=before.plans.find(row=>row.type==='fixed');if(!plan)throw new Error('F01_REQUIRED');
    try {
      const rule=before.rule_versions.find(row=>row.plan_id===plan.id&&row.kind==='weekday_mask');if(!rule)throw new Error('RULE_REQUIRED');
      const instant=plan.created_at_ms;
      let firstChanges=0,staleChanges=0,nextRevision=0;
      await executor.transaction(tx,async()=>{
        firstChanges=(await tx.run('UPDATE plans SET revision=revision+1 WHERE id=? AND revision=?',[plan.id,plan.revision])).changes;
        await tx.run("UPDATE app_meta SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT) WHERE key='data_revision'");
        await tx.run('INSERT INTO rule_versions(id,plan_id,kind,effective_on,revision,value_json,created_at_ms,cancelled_at_ms) VALUES(?,?,?,?,2,?,?,?)',[id(),plan.id,rule.kind,rule.effective_on,rule.value_json,instant,instant]);
      });
      const committed=await loadFacts(tx);
      await executor.transaction(tx,async()=>{staleChanges=(await tx.run('UPDATE plans SET name=?,revision=revision+1 WHERE id=? AND revision=?',['旧值覆盖',plan.id,plan.revision])).changes;});
      let rolledBack=false;
      try{await executor.transaction(tx,async()=>{await tx.run('UPDATE plans SET revision=revision+1 WHERE id=?',[plan.id]);await tx.run("UPDATE app_meta SET value='999999' WHERE key='data_revision'");throw new Error('ROLLBACK_PROBE');});}catch{rolledBack=true;}
      nextRevision=(await tx.first<{revision:number}>('SELECT max(revision)+1 AS revision FROM rule_versions WHERE plan_id=? AND kind=?',[plan.id,rule.kind]))!.revision;
      return {caseId:'AC119',rowId:'default',planId:plan.id,before,committed,after:await loadFacts(tx),firstChanges,staleChanges,rolledBack,nextRevision,...await info(tx)};
    } finally {await executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),before));}
  });
}
export async function runSqlCase(name:string){
  if(!sqlCaseNames.includes(name as SqlCaseName))throw new Error('UNSUPPORTED_SQL_CASE');
  return name==='serial_snapshot'?serialSnapshot():name==='cas'?cas():name==='cascade'?cascade():constraints(name as SqlCaseName);
}

async function cascade(){
  const executor=verificationExecutor();return executor.queue(async tx=>{
    const original=await loadFacts(tx),plan=original.plans.find(plan=>plan.type==='one_time');if(!plan)throw new Error('F01_REQUIRED');
    const due=original.rule_versions.find(rule=>rule.plan_id===plan.id&&rule.kind==='due_on');if(!due)throw new Error('DUE_RULE_REQUIRED');
    const resultId=id(),receiptId=id(),deleteReceipt=id(),eventId=id(),instant=plan.created_at_ms,on=plan.created_on;
    try{
      await executor.transaction(tx,async()=>{
        await tx.run('INSERT INTO one_time_results(id,plan_id,business_on,outcome,actual_completed_on,due_rule_version_id,note,entry_kind,submitted_at_ms,revision) VALUES(?,?,?,?,?,?,?,?,?,2)',[resultId,plan.id,on,'completed',on,due.id,'根删除当前备注','ordinary',instant]);
        await tx.run('INSERT INTO one_time_result_originals(result_id,original_outcome,original_note) VALUES(?,?,?)',[resultId,'failed','根删除原始备注']);
        await tx.run('INSERT INTO lifecycle_events(id,plan_id,kind,source_key,effective_on,effective_at_ms,reason,requested_at_ms) VALUES(?,?,?,?,?,?,?,?)',[eventId,plan.id,'archive',`user:${eventId}`,on,instant,'user',instant]);
        await tx.run('INSERT INTO command_receipts(command_id,plan_id,kind,payload_digest,result_code,object_id,issued_at_ms,committed_at_ms,expires_at_ms) VALUES(?,?,?,?,?,?,?,?,?)',[receiptId,plan.id,'ModifyOneTimeResult','a'.repeat(64),'OK',resultId,instant,instant,instant+604800000]);
      });
      const before=await loadFacts(tx);
      await executor.transaction(tx,async()=>{
        await tx.run("UPDATE command_receipts SET plan_id=NULL,object_id=NULL,payload_digest=NULL,result_code='TARGET_REMOVED' WHERE plan_id=?",[plan.id]);
        await tx.run('DELETE FROM plans WHERE id=?',[plan.id]);
        await tx.run('DELETE FROM app_meta WHERE key=?',[`reconciled_at:${plan.id}`]);
        await tx.run('INSERT INTO command_receipts(command_id,plan_id,kind,payload_digest,result_code,object_id,issued_at_ms,committed_at_ms,expires_at_ms) VALUES(?,NULL,?,NULL,?,NULL,?,?,?)',[deleteReceipt,'PermanentlyDeletePlan','TARGET_REMOVED',instant,instant,instant+604800000]);
      });
      return {before,after:await loadFacts(tx),planId:plan.id,resultId,receiptIds:[receiptId,deleteReceipt],committed:true,...await info(tx)};
    }finally{await executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),original));}
  });
}
