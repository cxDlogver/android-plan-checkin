import { openDatabaseAsync, SQLiteDatabase, SQLiteBindValue } from 'expo-sqlite';
import { getCalendars } from 'expo-localization';
import { DomainError, Facts, emptyFacts, metaValue, setMeta } from '../../domain/model';
import { initializeTimezone } from './timezone';
import { currentSchemaVersion, migrateDatabase } from './migrations';
import { now, beforeStorage } from '@verification/runtime';

export interface Tx {
  all<T>(sql: string, params?: SQLiteBindValue[]): Promise<T[]>;
  first<T>(sql: string, params?: SQLiteBindValue[]): Promise<T | null>;
  run(sql:string,params?:SQLiteBindValue[]):Promise<{changes:number}>;
  exec(sql:string):Promise<void>;
}
export const tableKeys = {app_meta:'key',plans:'id',rule_versions:'id',lifecycle_events:'id',cycle_records:'id',one_time_results:'id',cycle_record_originals:'record_id',one_time_result_originals:'result_id',command_receipts:'command_id'} as const;
export class DatabaseExecutor {
  private tail: Promise<unknown> = Promise.resolve();
  private constructor(private database:SQLiteDatabase){}
  static async open(){
    const database=await openDatabaseAsync('plan-checkin.db');
    const executor=new DatabaseExecutor(database);
    try {
      await database.execAsync('PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;');
      const mode=await database.getFirstAsync<{journal_mode:string}>('PRAGMA journal_mode'),sync=await database.getFirstAsync<{synchronous:number}>('PRAGMA synchronous'),fk=await database.getFirstAsync<{foreign_keys:number}>('PRAGMA foreign_keys');
      if(mode?.journal_mode!=='wal'||sync?.synchronous!==2||fk?.foreign_keys!==1)throw new DomainError('INIT_FAILED');
      await executor.queue(async tx=>{
        const version=await tx.first<{user_version:number}>('PRAGMA user_version');
        if((version?.user_version||0)>currentSchemaVersion)throw new DomainError('SCHEMA_TOO_NEW');
        await migrateDatabase(tx,version?.user_version||0);
        await executor.transaction(tx,async()=>{
          await initializeTimezone(tx,()=>getCalendars()[0]?.timeZone,now());
        });
      });
      return executor;
    }catch(error){await database.closeAsync();if(error instanceof DomainError)throw error;throw new DomainError('MIGRATION_FAILED');}
  }
  queue<T>(operation:(tx:Tx)=>Promise<T>):Promise<T>{
    const task=this.tail.then(async()=>{
      let active=true;const check=()=>{if(!active)throw new DomainError('STORAGE_IO');};
      const tx:Tx={all:async<T>(sql:string,params:SQLiteBindValue[]=[])=>{check();beforeStorage(sql);return this.database.getAllAsync<T>(sql,params);},first:async<T>(sql:string,params:SQLiteBindValue[]=[])=>{check();beforeStorage(sql);return this.database.getFirstAsync<T>(sql,params);},run:async(sql,params=[])=>{check();beforeStorage(sql);return this.database.runAsync(sql,params);},exec:async sql=>{check();beforeStorage(sql);await this.database.execAsync(sql);}};
      try{return await operation(tx);}finally{active=false;}
    });
    this.tail=task.catch(()=>undefined);return task;
  }
  async transaction<T>(tx:Tx,operation:()=>Promise<T>,readOnly=false){await tx.exec(readOnly?'BEGIN DEFERRED':'BEGIN IMMEDIATE');try{const result=await operation();await tx.exec('COMMIT');return result;}catch(error){await tx.exec('ROLLBACK');throw error;}}
  async diagnostics(){return this.queue(async tx=>({version:await tx.first('SELECT sqlite_version() AS version,sqlite_source_id() AS sourceId'),path:await tx.all('PRAGMA database_list'),journal:await tx.first('PRAGMA journal_mode'),synchronous:await tx.first('PRAGMA synchronous'),foreignKeys:await tx.first('PRAGMA foreign_keys'),userVersion:await tx.first('PRAGMA user_version')}));}
  async close(){return this.queue(async()=>this.database.closeAsync());}
}
export async function loadFacts(tx:Tx){const facts=emptyFacts();for(const table of Object.keys(tableKeys) as (keyof Facts)[]) (facts[table] as object[])=await tx.all<object>(`SELECT * FROM ${table}`);return facts;}
export async function persist(tx:Tx,before:Facts,after:Facts){
  const rows=(facts:Facts,table:keyof Facts)=>facts[table] as unknown as Record<string,SQLiteBindValue>[];
  // 删除前先将历史receipt转成无文本的防重放标记。
  for(const receipt of after.command_receipts)if(receipt.result_code==='TARGET_REMOVED'&&before.command_receipts.some(row=>row.command_id===receipt.command_id&&row.result_code!=='TARGET_REMOVED'))await tx.run('UPDATE command_receipts SET plan_id=NULL,object_id=NULL,payload_digest=NULL,result_code=? WHERE command_id=?',['TARGET_REMOVED',receipt.command_id]);
  for(const table of [...Object.keys(tableKeys)].reverse() as (keyof Facts)[]){const key=tableKeys[table],ids=new Set(rows(after,table).map(row=>row[key]));for(const row of rows(before,table))if(!ids.has(row[key]))await tx.run(`DELETE FROM ${table} WHERE ${key}=?`,[row[key]!]);}
  for(const table of Object.keys(tableKeys) as (keyof Facts)[]){const key=tableKeys[table],old=new Map(rows(before,table).map(row=>[row[key],row]));for(const row of rows(after,table)){
    const previous=old.get(row[key]);if(JSON.stringify(previous)===JSON.stringify(row))continue;
    const columns=Object.keys(row);if(!previous)await tx.run(`INSERT INTO ${table} (${columns.join(',')}) VALUES (${columns.map(()=>'?').join(',')})`,columns.map(column=>row[column]!));
    else {const changed=columns.filter(column=>column!==key&&previous[column]!==row[column]);if(changed.length){const cas=typeof previous.revision==='number';const result=await tx.run(`UPDATE ${table} SET ${changed.map(column=>`${column}=?`).join(',')} WHERE ${key}=?${cas?' AND revision=?':''}`,[...changed.map(column=>row[column]!),row[key]!,...(cas?[previous.revision!]:[])]);if(cas&&result.changes!==1)throw new DomainError(table==='plans'?'PLAN_CHANGED':'RECORD_CHANGED');}}
  }}
  const violations=await tx.all('PRAGMA foreign_key_check');if(violations.length)throw new DomainError('STORAGE_IO');
}
