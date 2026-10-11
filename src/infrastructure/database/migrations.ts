import { DomainError } from '../../domain/model';
import type { Tx } from './executor';
import { schemaV1 } from './schema';

export const currentSchemaVersion=1;
export interface Migration { version:number; sql:string; validate?:(tx:Tx)=>Promise<void> }
const migrations:readonly Migration[]=[{version:1,sql:schemaV1}];

// Every pending step, its checks, and the final version belong to one transaction.
export async function migrateDatabase(tx:Tx,version:number,steps:readonly Migration[]=migrations){
  const target=steps.at(-1)?.version??version;
  if(!Number.isInteger(version)||version<0||steps.some((step,index)=>step.version!==index+1))throw new DomainError('MIGRATION_FAILED');
  if(version>target)throw new DomainError('SCHEMA_TOO_NEW');
  if(version===target)return;
  let begun=false;
  try{
    await tx.exec('BEGIN IMMEDIATE');begun=true;
    for(const step of steps.filter(step=>step.version>version)){
      await tx.exec(step.sql);
      await step.validate?.(tx);
    }
    if((await tx.all('PRAGMA foreign_key_check')).length)throw new DomainError('MIGRATION_FAILED');
    await tx.exec(`PRAGMA user_version=${target}`);
    await tx.exec('COMMIT');begun=false;
  }catch{
    if(begun)try{await tx.exec('ROLLBACK');}catch{/* Preserve the file if the connection itself has failed. */}
    throw new DomainError('MIGRATION_FAILED');
  }
}
