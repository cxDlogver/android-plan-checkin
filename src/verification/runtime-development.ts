import type { DatabaseExecutor } from '../infrastructure/database/executor';
let instant:number|null=null;
let fault:'before_commit'|'before_commit_io'|'after_commit'|null=null;
let executor:DatabaseExecutor|undefined;
let attachments=0;
export const now=()=>instant??Date.now();
export function setClock(value:number|null){if(value!==null&&!Number.isSafeInteger(value))throw new Error('Invalid test instant');instant=value;}
export function injectFault(value:typeof fault){fault=value;}
export function beforeStorage(sql:string){if((fault==='before_commit'||fault==='before_commit_io')&&sql==='COMMIT'){const full=fault==='before_commit';fault=null;throw new Error(full?'SQLITE_FULL: development before-commit fault':'SQLITE_IOERR: development before-commit fault');}}
export function afterUserCommit(){if(fault==='after_commit'){fault=null;throw new Error('SQLITE_IOERR: development lost commit acknowledgement');}}
export function attachExecutor(value:DatabaseExecutor){attachments++;executor=value;}
export function verificationExecutor(){if(!executor)throw new Error('Verification database unavailable');return executor;}
export function developmentRuntimeInfo(){return {attachments,hasExecutor:!!executor};}
