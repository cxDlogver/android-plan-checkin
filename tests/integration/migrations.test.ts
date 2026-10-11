import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { DatabaseExecutor, loadFacts, persist } from '../../src/infrastructure/database/executor';
import { migrateDatabase, Migration } from '../../src/infrastructure/database/migrations';
import { buildFixture } from '../../src/verification/fixtures';
const adapter=require(path.resolve('tests/integration/host-adapter.cjs')) as {state:{filename:string;fault:((sql:string)=>boolean)|null;trace:string[];zone:string}};
const state=adapter.state;
function registry(second:string):Migration[]{return [{version:1,sql:''},{version:2,sql:"CREATE TABLE migration_first(value TEXT NOT NULL) STRICT; INSERT INTO migration_first VALUES ('first'); UPDATE plans SET description='uncommitted migration';"},{version:3,sql:second}];}
async function seeded(){state.filename=path.resolve('.artifacts/integration-databases',`${randomUUID()}.db`);state.fault=null;state.zone='Asia/Shanghai';state.trace=[];const executor=await DatabaseExecutor.open();await executor.queue(tx=>executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),buildFixture('F01','2026-10-10',state.zone))));return executor;}
async function inspect(executor:DatabaseExecutor){return executor.queue(async tx=>({facts:await loadFacts(tx),schema:await tx.all("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name"),version:await tx.first<{user_version:number}>('PRAGMA user_version'),foreignKeys:await tx.all('PRAGMA foreign_key_check')}));}
for(const [name,second]of [['second SQL error','INSERT INTO missing_migration_table VALUES (1)'],['deferred foreign key failure',"CREATE TABLE migration_fk(value TEXT REFERENCES plans(id) DEFERRABLE INITIALLY DEFERRED) STRICT; INSERT INTO migration_fk VALUES ('missing-plan')"]] as const){
  test(`migration chain rolls back first-step DDL and every fact after ${name}`,async()=>{
    const executor=await seeded(),before=await inspect(executor);
    state.trace=[];
    await assert.rejects(()=>executor.queue(tx=>migrateDatabase(tx,1,registry(second))),(error:{code?:string})=>error.code==='MIGRATION_FAILED');
    if(name==='deferred foreign key failure'){assert.ok(state.trace.includes('PRAGMA foreign_key_check'));assert.ok(!state.trace.includes('PRAGMA user_version=3'));}
    assert.deepEqual(await inspect(executor),before);await executor.close();
    const db=new DatabaseSync(state.filename,{readOnly:true});try{assert.equal(db.prepare('PRAGMA user_version').get()!.user_version,1);assert.equal(db.prepare("SELECT count(*) count FROM sqlite_master WHERE name='migration_first'").get()!.count,0);}finally{db.close();}
  });
}
test('migration chain commits once after both validated steps and writes the version last',async()=>{
  const executor=await seeded();state.trace=[];
  const steps=registry("CREATE TABLE migration_second(value INTEGER NOT NULL) STRICT; INSERT INTO migration_second VALUES (2)");
  await executor.queue(tx=>migrateDatabase(tx,1,steps));
  const after=await inspect(executor);assert.equal(after.version?.user_version,3);assert.deepEqual(after.foreignKeys,[]);assert.ok(after.facts.plans.every(plan=>plan.description==='uncommitted migration'));
  assert.equal(state.trace.filter(sql=>sql==='BEGIN IMMEDIATE').length,1);assert.equal(state.trace.filter(sql=>sql==='COMMIT').length,1);assert.ok(state.trace.indexOf('PRAGMA user_version=3')>state.trace.indexOf(steps[2]!.sql));
  await executor.close();
});
