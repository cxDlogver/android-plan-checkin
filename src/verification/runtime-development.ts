import type { DatabaseExecutor } from '../infrastructure/database/executor';
import type { Envelope } from '../domain/model';
let instant:number|null=null;
let fault:'before_commit'|'before_commit_io'|'before_commit_busy'|'after_commit'|'before_commit_hold'|'after_commit_hold'|'read_hold'|'read_io'|null=null;
let reached:string|null=null;
let writeTransaction=false;
let envelope:Envelope|null=null;
let executor:DatabaseExecutor|undefined;
let attachments=0;
let releaseGate:(()=>void)|null=null;
let readInitialization:(()=>Promise<void>)|undefined;
let versionOverride: {version:string|null;build:string|null}|undefined;
let storageFailure:{code:string;nativeType:string;sqliteSignal:string;atMs:number}|null=null;
export const now=()=>instant??Date.now();
export function setClock(value:number|null){if(value!==null&&!Number.isSafeInteger(value))throw new Error('Invalid test instant');instant=value;}
export function injectFault(value:typeof fault){releaseGate?.();releaseGate=null;fault=value;reached=null;envelope=null;storageFailure=null;}
export function observeUserCommand(value:Envelope){envelope=JSON.parse(JSON.stringify(value)) as Envelope;}
export function observeStorageFailure(code:string,error:unknown){const message=String(error);storageFailure={code,nativeType:error instanceof Error?error.name:typeof error,sqliteSignal:message.match(/SQLITE_[A-Z_]+|disk I\/O error|database or disk is full|database is locked/i)?.[0]||'unclassified native rejection',atMs:now()};}
export const faultStatus=()=>({armed:fault,reached,envelope,storageFailure});
function hold(point:string){reached=point;console.info(`PlanCheckinVerificationGate:${point}`);return new Promise<void>(resolve=>{releaseGate=resolve;});}
export function beforeStorage(sql:string):void|Promise<void>{if(fault==='read_hold'&&/^SELECT/i.test(sql)){fault=null;return hold('read_hold');}if(fault==='read_io'&&/^SELECT/i.test(sql)){fault=null;throw new Error('SQLITE_IOERR: development read fault');}if(sql.startsWith('BEGIN'))writeTransaction=sql==='BEGIN IMMEDIATE';if(sql==='COMMIT'&&writeTransaction){if(fault==='before_commit_hold')return hold(fault);if(fault==='before_commit'||fault==='before_commit_io'||fault==='before_commit_busy'){const point=fault;fault=null;throw new Error(point==='before_commit'?'SQLITE_FULL: development before-commit fault':point==='before_commit_busy'?'SQLITE_BUSY: development before-commit fault':'SQLITE_IOERR: development before-commit fault');}}}
export function afterUserCommit():void|Promise<void>{if(fault==='after_commit_hold')return hold(fault);if(fault==='after_commit'){fault=null;throw new Error('SQLITE_IOERR: development lost commit acknowledgement');}}
export function attachExecutor(value:DatabaseExecutor){attachments++;executor=value;}
export function verificationExecutor(){if(!executor)throw new Error('Verification database unavailable');return executor;}
export function developmentRuntimeInfo(){return {attachments,hasExecutor:!!executor};}
export function attachReadInitialization(callback:()=>Promise<void>){readInitialization=callback;}
export function beginReadInitialization(){if(!readInitialization)throw new Error('READ_INITIALIZATION_UNAVAILABLE');void readInitialization();}
export function overrideSettingsVersion(value:typeof versionOverride){versionOverride=value;}
export function settingsVersion(version:string|null,build:string|null){return versionOverride||{version,build};}
