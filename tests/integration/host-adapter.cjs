// Host SQLite integration only. Production code never imports this adapter.
const {DatabaseSync}=require('node:sqlite');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve('.artifacts/integration-databases');fs.mkdirSync(root,{recursive:true});
const state={filename:path.join(root,'current.db'),opens:0,closes:0,trace:[],fault:null,ackFault:false,zone:'Asia/Shanghai'};
function fail(sql){state.trace.push(sql);if(state.fault?.(sql)){state.fault=null;throw new Error('SQLITE_FULL: injected storage failure');}}
async function openDatabaseAsync(){state.opens++;const db=new DatabaseSync(state.filename);return {
  execAsync:async sql=>{fail(sql);db.exec(sql);},
  getAllAsync:async(sql,params=[])=>{fail(sql);return db.prepare(sql).all(...params);},
  getFirstAsync:async(sql,params=[])=>{fail(sql);return db.prepare(sql).get(...params)||null;},
  runAsync:async(sql,params=[])=>{fail(sql);const result=db.prepare(sql).run(...params);return {changes:Number(result.changes),lastInsertRowId:Number(result.lastInsertRowid)};},
  closeAsync:async()=>{state.closes++;db.close();},
};}
module.exports={state,now:Date.now,beforeStorage:()=>{},afterUserCommit:()=>{if(state.ackFault){state.ackFault=false;throw new Error('SQLITE_IOERR: lost acknowledgement');}},attachExecutor:()=>{},openDatabaseAsync,getCalendars:()=>[{timeZone:state.zone}],randomUUID:crypto.randomUUID,CryptoDigestAlgorithm:{SHA256:'SHA256'},digestStringAsync:async(_,value)=>crypto.createHash('sha256').update(value).digest('hex')};
