import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { DatabaseExecutor } from '../../src/infrastructure/database/executor';
import { schemaV1 } from '../../src/infrastructure/database/schema';
import { schemaV2 } from '../../src/infrastructure/database/schema-v2';
import { currentSchemaVersion } from '../../src/infrastructure/database/migrations';
const {state}=require(path.resolve('tests/integration/host-adapter.cjs')) as {state:{filename:string;fault:null;trace:string[];zone:string}};
test('schema 3 is blocked by the schema-2 executor without row, trigger or timezone changes',async()=>{
 state.filename=path.resolve('.artifacts/integration-databases',randomUUID()+'.db');state.fault=null;state.trace=[];state.zone='America/New_York';
 const db=new DatabaseSync(state.filename);db.exec(schemaV1);db.exec(schemaV2);db.exec("INSERT INTO app_meta VALUES('app_timezone','Asia/Shanghai'); PRAGMA user_version=3");
 const before={meta:db.prepare('SELECT * FROM app_meta ORDER BY key').all(),schema:db.prepare('SELECT name,type,sql FROM sqlite_master ORDER BY name').all()};db.close();
 assert.equal(currentSchemaVersion,2);await assert.rejects(()=>DatabaseExecutor.open(),(error:unknown)=>!!error&&typeof error==='object'&&'code'in error&&error.code==='SCHEMA_TOO_NEW');
 const after=new DatabaseSync(state.filename);try{assert.equal(after.prepare('PRAGMA user_version').get()!.user_version,3);assert.deepEqual(after.prepare('SELECT * FROM app_meta ORDER BY key').all(),before.meta);assert.deepEqual(after.prepare('SELECT name,type,sql FROM sqlite_master ORDER BY name').all(),before.schema);assert.equal(state.trace.some(sql=>/^\s*(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|BEGIN)/i.test(sql)),false);}finally{after.close();}
});
