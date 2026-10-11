import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { DatabaseExecutor, loadFacts, persist, Tx } from '../../src/infrastructure/database/executor';
import { schemaV1 } from '../../src/infrastructure/database/schema';
import { migrateDatabase } from '../../src/infrastructure/database/migrations';
import { immutableTables } from '../../src/infrastructure/database/schema-v2';
import { migrationV2Given } from '../../src/verification/migration-v2-given';
const adapter=require(path.resolve('tests/integration/host-adapter.cjs')) as {state:{filename:string;fault:((sql:string)=>boolean)|null;trace:string[];zone:string}};
const state=adapter.state;
function tx(db:DatabaseSync):Tx{return {exec:async sql=>{db.exec(sql);},all:async<T>(sql:string,params=[])=>db.prepare(sql).all(...params as import('node:sqlite').SQLInputValue[]) as T[],first:async<T>(sql:string,params=[])=>db.prepare(sql).get(...params as import('node:sqlite').SQLInputValue[]) as T||null,run:async(sql,params=[])=>({changes:Number(db.prepare(sql).run(...params as import('node:sqlite').SQLInputValue[]).changes)})};}
async function legacy(){state.filename=path.resolve('.artifacts/integration-databases',`${randomUUID()}.db`);state.fault=null;state.trace=[];state.zone='America/New_York';const db=new DatabaseSync(state.filename);db.exec('PRAGMA foreign_keys=ON');db.exec(schemaV1);const t=tx(db);await persist(t,await loadFacts(t),migrationV2Given());db.exec('PRAGMA user_version=1');db.close();}
test('schema 1→2 preserves all nine-table facts, fixed zone, originals and future applications',async()=>{
 await legacy();const executor=await DatabaseExecutor.open();try{assert.deepEqual(JSON.parse(JSON.stringify(await executor.queue(loadFacts))),migrationV2Given());const d=await executor.diagnostics() as {userVersion:{user_version:number}};assert.equal(d.userVersion.user_version,2);const triggers=await executor.queue(tx=>tx.all<{name:string}>("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"));assert.deepEqual(triggers.map(t=>t.name),immutableTables.map(t=>'immutable_'+t).sort());assert.deepEqual(await executor.queue(tx=>tx.all('PRAGMA foreign_key_check')),[]);}finally{await executor.close();}
});
test('seven guards reject real frozen-field rewrites while legal mutable fields and cascade remain usable',async()=>{
 await legacy();const executor=await DatabaseExecutor.open();try{
  const before=await executor.queue(loadFacts);
  for(const [table,column,value]of [['plans','starts_on','2026-10-10'],['cycle_records','business_on','2026-10-01'],['one_time_results','due_rule_version_id','forged'],['cycle_record_originals','original_note','forged'],['one_time_result_originals','original_note','forged'],['rule_versions','value_json','{"weeklyTarget":7}'],['lifecycle_events','reason','historical_terminal']])await assert.rejects(()=>executor.queue(tx=>tx.run(`UPDATE ${table} SET ${column}=?`,[value!])),/immutable/);
  assert.deepEqual(await executor.queue(loadFacts),before);
  await executor.queue(tx=>executor.transaction(tx,async()=>{await tx.run("UPDATE plans SET name='合法名称',description='合法说明',revision=revision+1");await tx.run("UPDATE cycle_records SET result='skip',note='合法备注',modified_at_ms=submitted_at_ms+1,revision=revision+1");await tx.run("UPDATE one_time_results SET outcome='failed',actual_completed_on=NULL,note='合法更正',modified_at_ms=submitted_at_ms+1,revision=revision+1");await tx.run('UPDATE rule_versions SET cancelled_at_ms=created_at_ms+1');await tx.run('UPDATE lifecycle_events SET cancelled_at_ms=requested_at_ms+1');}));
  assert.deepEqual((await executor.queue(loadFacts)).cycle_record_originals,before.cycle_record_originals);
  await executor.queue(tx=>tx.run('DELETE FROM plans'));const after=await executor.queue(loadFacts);assert.equal(after.plans.length+after.rule_versions.length+after.lifecycle_events.length+after.cycle_records.length+after.one_time_results.length+after.cycle_record_originals.length+after.one_time_result_originals.length,0);
 }finally{await executor.close();}
});
test('schema 2 validation failure rolls back every added guard, version and all legacy facts',async()=>{
 await legacy();const db=new DatabaseSync(state.filename),t=tx(db);try{const before=await loadFacts(t);await assert.rejects(()=>migrateDatabase({...t,exec:async sql=>{if(sql==='PRAGMA user_version=2')throw new Error('controlled failure before version write');await t.exec(sql);}},1));assert.equal(db.prepare('PRAGMA user_version').get()!.user_version,1);assert.equal(db.prepare("SELECT count(*) n FROM sqlite_master WHERE type='trigger'").get()!.n,0);assert.deepEqual(await loadFacts(t),before);}finally{db.close();}
});
