import { loadFacts } from '../infrastructure/database/executor';
import { migrateDatabase } from '../infrastructure/database/migrations';
import { immutableTables } from '../infrastructure/database/schema-v2';
import { migrationV2Given } from './migration-v2-given';
import { verificationExecutor } from './runtime-development';
import { persist } from '../infrastructure/database/executor';

export async function migrationV2Probe(){
 const executor=verificationExecutor();
 await executor.queue(tx=>executor.transaction(tx,async()=>{
  for(const table of immutableTables)await tx.exec(`DROP TRIGGER IF EXISTS immutable_${table}`);
  await persist(tx,await loadFacts(tx),migrationV2Given());
  await tx.exec('PRAGMA user_version=1');
 }));
 const before=await executor.queue(async tx=>({facts:await loadFacts(tx),version:await tx.first('PRAGMA user_version'),schema:await tx.all("SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','index','trigger') ORDER BY type,name")}));
 await executor.queue(tx=>migrateDatabase(tx,1));
 const after=await executor.queue(async tx=>({facts:await loadFacts(tx),version:await tx.first('PRAGMA user_version'),schema:await tx.all("SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','index','trigger') ORDER BY type,name"),foreignKeyCheck:await tx.all('PRAGMA foreign_key_check')}));
 const rejected=[];
 for(const [table,column,value]of [['plans','starts_on','2026-10-10'],['cycle_records','business_on','2026-10-01'],['one_time_results','due_rule_version_id','forged'],['cycle_record_originals','original_note','forged'],['one_time_result_originals','original_note','forged'],['rule_versions','value_json','{"weeklyTarget":7}'],['lifecycle_events','reason','historical_terminal']]){
  try{await executor.queue(tx=>tx.run(`UPDATE ${table} SET ${column}=?`,[value!]));rejected.push({table,column,rejected:false});}
  catch(error){rejected.push({table,column,rejected:String(error).includes('immutable'),nativeError:String(error)});}
 }
 const retained=await executor.queue(loadFacts);
 return {scope:'Controlled schema-1 Given in the isolated development database, followed by the unchanged production migration executor. Formal APK upgrade is a separate gate.',before,after,rejected,retained};
}
