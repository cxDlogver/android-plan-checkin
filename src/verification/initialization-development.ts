import { SQLiteDatabase } from 'expo-sqlite';
import { bootstrap } from '../application/service';
import { DomainError } from '../domain/model';
import { DatabaseExecutor, loadFacts } from '../infrastructure/database/executor';
import { developmentRuntimeInfo, verificationExecutor } from './runtime-development';

export async function connectionInfo(){
  const services=await Promise.all(Array.from({length:5},()=>bootstrap()));
  return {...developmentRuntimeInfo(),sameService:services.every(service=>service===services[0]),requests:services.length};
}
export async function initializationProbe(kind:string){
  if(!['invalid_parameters','schema_too_new'].includes(kind))throw new Error('INVALID_INITIALIZATION_PROBE');
  const existing=verificationExecutor();
  const before=await existing.queue(async tx=>({facts:await loadFacts(tx),schema:await tx.all("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name"),userVersion:await tx.first<{user_version:number}>('PRAGMA user_version')}));
  if(kind==='schema_too_new')await existing.queue(tx=>tx.exec(`PRAGMA user_version=${Number(before.userVersion?.user_version)+1}`));
  await existing.close();
  const original=SQLiteDatabase.prototype.getFirstAsync;
  let injected=false,observedJournal:unknown=null,handedOut=false,code:string|null=null;
  if(kind==='invalid_parameters'){
    const instrumented=async function(this:SQLiteDatabase,...args:unknown[]):Promise<unknown>{
      if(args[0]==='PRAGMA journal_mode'&&!injected){
        injected=true;await this.execAsync('PRAGMA journal_mode=DELETE');
        const actual=await Reflect.apply(original,this,args);observedJournal=actual;return actual;
      }
      return Reflect.apply(original,this,args);
    };
    // Reflect.apply forwards both SDK overloads without changing their bind parameters.
    SQLiteDatabase.prototype.getFirstAsync=instrumented as typeof original;
  }
  try{const candidate=await DatabaseExecutor.open();handedOut=true;await candidate.close();}
  catch(error){code=error instanceof DomainError?error.code:'UNEXPECTED_INITIALIZATION_FAILURE';}
  finally{SQLiteDatabase.prototype.getFirstAsync=original;}
  return {kind,before,injected,observedJournal,handedOut,code,originalConnectionClosed:true,restartRequired:true};
}
