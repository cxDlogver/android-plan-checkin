import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { AppService } from '../../src/application/service';
import { DatabaseExecutor, loadFacts, persist } from '../../src/infrastructure/database/executor';
import { buildFixture, fixtureNames } from '../../src/verification/fixtures';
import { dayMs } from '../../src/domain/date';
import { Envelope } from '../../src/domain/model';
const adapter=require(path.resolve('tests/integration/host-adapter.cjs')) as {state:{filename:string;opens:number;closes:number;trace:string[];fault:((sql:string)=>boolean)|null;ackFault:boolean;zone:string}};
const state=adapter.state,zone='Asia/Shanghai',now=dayMs('2026-10-10',zone)+3600000;
function fresh(){state.filename=path.resolve('.artifacts/integration-databases',`${randomUUID()}.db`);state.trace=[];state.fault=null;state.zone=zone;}
function create(planId=randomUUID()):Envelope{return {commandId:randomUUID(),issuedAtMs:now,kind:'CreatePlan',payload:{planId,name:'原子计划',description:'',type:'fixed',direction:'do',startsOn:'2026-10-10',endOn:null,weekdayMask:127}};}
test('真实宿主SQLite迁移9表/STRICT/外键、重开保留固定时区，单连接串行且tx不可逃逸',async()=>{
  fresh();const opens=state.opens,executor=await DatabaseExecutor.open();
  const diagnostics=await executor.diagnostics() as {journal:{journal_mode:string};foreignKeys:{foreign_keys:number};userVersion:{user_version:number}};
  assert.equal(diagnostics.journal.journal_mode,'wal');assert.equal(diagnostics.foreignKeys.foreign_keys,1);assert.equal(diagnostics.userVersion.user_version,1);
  const tables=await executor.queue(tx=>tx.all<{name:string;strict:number}>('PRAGMA table_list'));assert.equal(tables.filter(t=>t.name!=='sqlite_schema'&&t.name!=='sqlite_temp_schema').length,9);assert.ok(tables.filter(t=>!t.name.startsWith('sqlite_')).every(t=>t.strict===1));
  let escaped:Parameters<Parameters<typeof executor.queue>[0]>[0]|undefined;const order:number[]=[];
  await Promise.all([executor.queue(async tx=>{escaped=tx;order.push(1);await new Promise(r=>setTimeout(r,15));order.push(2);}),executor.queue(async()=>{order.push(3);})]);assert.deepEqual(order,[1,2,3]);await assert.rejects(()=>escaped!.first('SELECT 1'));
  assert.equal(state.opens-opens,1);await executor.close();state.zone='America/New_York';const reopened=await DatabaseExecutor.open();const facts=await reopened.queue(loadFacts);assert.equal(facts.app_meta.find(m=>m.key==='app_timezone')?.value,zone);await reopened.close();
});
test('迁移中断整体回滚user_version与DDL，高版本阻断且不删除原数据',async()=>{
  fresh();state.fault=sql=>sql==='PRAGMA user_version=1';await assert.rejects(()=>DatabaseExecutor.open());
  let db=new DatabaseSync(state.filename);assert.equal(db.prepare('PRAGMA user_version').get()!.user_version,0);assert.equal(db.prepare("SELECT count(*) n FROM sqlite_master WHERE type='table'").get()!.n,0);db.exec('CREATE TABLE sentinel(value TEXT); INSERT INTO sentinel VALUES (\'保留\'); PRAGMA user_version=2');db.close();
  await assert.rejects(()=>DatabaseExecutor.open(),(e:{code?:string})=>e.code==='SCHEMA_TOO_NEW');db=new DatabaseSync(state.filename);assert.equal(db.prepare('SELECT value FROM sentinel').get()!.value,'保留');db.close();
});
test('写入中断无业务/receipt/revision半提交，同信封重试与并发重复只有一份事实',async()=>{
  fresh();const executor=await DatabaseExecutor.open(),service=new AppService(executor,()=>now),envelope=create();
  state.fault=sql=>sql.startsWith('INSERT INTO command_receipts');const failed=await service.execute(envelope);assert.equal(failed.ok,false);assert.equal(failed.code,'STORAGE_FULL');let snapshot=await service.snapshot();assert.equal(snapshot.facts.plans.length,0);assert.equal(snapshot.dataRevision,0);assert.equal(snapshot.facts.command_receipts.length,0);
  const results=await Promise.all([service.execute(envelope),service.execute(envelope),service.execute(envelope)]);assert.ok(results.every(r=>r.ok));assert.equal(results.filter(r=>r.ok&&r.replayed).length,2);snapshot=await service.snapshot();assert.equal(snapshot.facts.plans.length,1);assert.equal(snapshot.facts.command_receipts.length,1);assert.equal(snapshot.dataRevision,1);await executor.close();
});
test('级联永久删除清除历史及文本/摘要，原成功receipt保留无内容防重放标记',async()=>{
  fresh();const executor=await DatabaseExecutor.open(),service=new AppService(executor,()=>now),envelope=create(),planId=envelope.payload.planId;
  assert.equal((await service.execute(envelope)).ok,true);await executor.queue(tx=>tx.run('INSERT INTO app_meta(key,value) VALUES (?,?)',[`reconciled_at:${planId}`,String(now)]));let snapshot=await service.snapshot();
  const management=(kind:Envelope['kind'],revision:number):Envelope=>({commandId:randomUUID(),issuedAtMs:now,kind,payload:{planId,expectedPlanRevision:revision,...(kind==='ArchivePlan'?{eventId:randomUUID()}:{})}});
  assert.equal((await service.execute(management('ArchivePlan',snapshot.facts.plans[0]!.revision))).ok,true);snapshot=await service.snapshot();assert.equal((await service.execute(management('PermanentlyDeletePlan',snapshot.facts.plans[0]!.revision))).ok,true);snapshot=await service.snapshot();assert.equal(snapshot.facts.plans.length,0);assert.equal(snapshot.facts.rule_versions.length,0);assert.equal(snapshot.facts.lifecycle_events.length,0);assert.equal(snapshot.facts.app_meta.some(m=>m.key===`reconciled_at:${planId}`),false);assert.ok(snapshot.facts.command_receipts.every(r=>r.result_code==='TARGET_REMOVED'&&r.payload_digest===null&&r.object_id===null&&r.plan_id===null));assert.equal((await service.execute(envelope)).code,'TARGET_REMOVED');await executor.close();
});
test('提交成功后返回丢失按原信封读receipt，不能重复创建',async()=>{
  fresh();const executor=await DatabaseExecutor.open(),service=new AppService(executor,()=>now),envelope=create();state.ackFault=true;
  assert.equal((await service.execute(envelope)).code,'STORAGE_IO');assert.equal((await service.snapshot()).facts.plans.length,1);const retry=await service.execute(envelope);assert.equal(retry.ok,true);assert.ok(retry.ok&&retry.replayed);assert.equal((await service.snapshot()).facts.plans.length,1);await executor.close();
});
test('F01–F08及100计划/10000记录性能夹具遵守真实9表约束',async()=>{
  for(const name of fixtureNames){fresh();const executor=await DatabaseExecutor.open();const facts=buildFixture(name,'2026-10-10',zone);assert.deepEqual(buildFixture(name,'2026-10-10',zone),facts);await executor.queue(tx=>executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),facts)));const actual=await executor.queue(loadFacts);assert.equal(actual.plans.length,facts.plans.length);assert.equal(actual.cycle_records.length,facts.cycle_records.length);if(name==='PERF'){assert.equal(actual.plans.length,100);assert.equal(actual.cycle_records.length,10000);assert.deepEqual(['fixed','weekly','one_time'].map(type=>actual.plans.filter(plan=>plan.type===type).length),[40,40,20]);const dates=actual.cycle_records.map(record=>record.business_on).sort();assert.equal(dates[0],'2023-10-10');assert.equal(dates.at(-1),'2026-10-09');assert.equal(actual.one_time_results.length,10);}await executor.close();}
});
