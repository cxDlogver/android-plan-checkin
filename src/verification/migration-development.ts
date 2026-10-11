import { DomainError } from '../domain/model';
import { loadFacts, Tx } from '../infrastructure/database/executor';
import { migrateDatabase, Migration } from '../infrastructure/database/migrations';
import { verificationExecutor } from './runtime-development';

let observation:Record<string,unknown>|undefined;
export function migrationStatus(){return observation??{phase:'idle'};}
export async function migrationProbe(kind:string){
  if(!['sql_error','process_before_commit'].includes(kind))throw new Error('INVALID_MIGRATION_PROBE');
  if(observation?.phase==='running'||observation?.phase==='before_commit')throw new Error('MIGRATION_PROBE_RUNNING');
  const executor=verificationExecutor();
  const before=await executor.queue(async tx=>({facts:await loadFacts(tx),schema:await tx.all("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name"),version:await tx.first<{user_version:number}>('PRAGMA user_version')}));
  if(before.version?.user_version!==1)throw new Error('MIGRATION_PROBE_REQUIRES_V1');
  observation={kind,phase:'running',before};
  const state=observation;
  const steps:Migration[]=[{version:1,sql:''},{version:2,sql:"CREATE TABLE migration_probe_one(value TEXT NOT NULL) STRICT; INSERT INTO migration_probe_one VALUES ('first step'); UPDATE plans SET description=description||' migration probe';"},{version:3,sql:"CREATE TABLE migration_probe_two(value INTEGER NOT NULL) STRICT; INSERT INTO migration_probe_two VALUES (2);",validate:async tx=>{
    state.pending={facts:await loadFacts(tx),schema:await tx.all("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name")};
    if(kind==='sql_error')await tx.exec('INSERT INTO migration_probe_missing VALUES (1)');
  }}];
  void executor.queue(async tx=>{
    const guarded:Tx={...tx,exec:async sql=>{
      if(kind==='process_before_commit'&&sql==='COMMIT'){
        state.pendingVersion=await tx.first('PRAGMA user_version');state.phase='before_commit';
        await new Promise<void>(()=>{});
      }
      await tx.exec(sql);
    }};
    try{await migrateDatabase(guarded,1,steps);state.code='UNEXPECTED_MIGRATION_SUCCESS';}
    catch(error){state.code=error instanceof DomainError?error.code:'UNEXPECTED_MIGRATION_ERROR';}
    if(kind==='sql_error')state.after={facts:await loadFacts(tx),schema:await tx.all("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name"),version:await tx.first('PRAGMA user_version'),foreignKeyCheck:await tx.all('PRAGMA foreign_key_check')};
    state.phase='finished';
  }).catch(error=>{state.phase='failed';state.error=String(error);});
  return state;
}
