import { Platform } from 'react-native';
import * as Application from 'expo-application';
import * as Font from 'expo-font';
import { router } from 'expo-router';
import { DateTime } from 'luxon';
import type { AppService } from '../application/service';
import type { Envelope, Snapshot } from '../domain/model';
import { setMeta } from '../domain/model';
import { businessToday, validZone } from '../domain/date';
import { loadFacts, persist } from '../infrastructure/database/executor';
import { buildFixture, fixtureNames, FixtureName } from './fixtures';
import { injectFault, now, setClock, verificationExecutor } from './runtime-development';
import { runSqlCase } from './sql-cases-development';
import { connectionInfo, initializationProbe } from './initialization-development';

type Context = { service:AppService; refresh:(clearPins?:boolean)=>Promise<Snapshot|undefined> };
type Request = { id:string; action:string; payload?:Record<string,unknown> };
const applicationId = 'com.xiang.plancheckin.dev';
const contextId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
let context:Context|undefined;
let socket:WebSocket|undefined;
let reconnect:ReturnType<typeof setTimeout>|undefined;
let pending:Promise<unknown> = Promise.resolve();

function requireIsolated(){
  if(!__DEV__||Application.applicationId!==applicationId) throw new Error('ISOLATED_DEVELOPMENT_ONLY');
}
async function dispatch({action,payload={}}:Request){
  requireIsolated();
  if(!context) throw new Error('APPLICATION_NOT_READY');
  switch(action){
    case 'capture': {
      const snapshot=await context.service.snapshot();
      return {contextId,applicationId:Application.applicationId,api:Platform.Version,clock:now(),sqlite:await context.service.diagnostics(),fonts:['NotoSC400','NotoSC600','NotoSC700'].map(name=>({name,loaded:Font.isLoaded(name)})),snapshot};
    }
    case 'clock': {
      const value=payload.instant;
      if(value===null) setClock(null);
      else {
        if(typeof value!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(value)) throw new Error('INVALID_TEST_INSTANT');
        const parsed=DateTime.fromISO(value,{setZone:true});
        if(!parsed.isValid) throw new Error('INVALID_TEST_INSTANT');
        setClock(parsed.toMillis());
      }
      const snapshot=await context.refresh(true);
      if(!snapshot) throw new Error('REFRESH_FAILED');
      return {contextId,clock:now(),today:snapshot.today,asOfMs:snapshot.asOfMs,zone:snapshot.zone};
    }
    case 'fixture': {
      if(payload.confirm!=='RESET_ISOLATED_DEV_DATABASE') throw new Error('RESET_CONFIRMATION_REQUIRED');
      if(!fixtureNames.includes(payload.name as FixtureName)||typeof payload.zone!=='string'||!validZone(payload.zone)) throw new Error('INVALID_FIXTURE');
      const name=payload.name as FixtureName,zone=payload.zone;
      injectFault(null);
      const executor=verificationExecutor();
      await executor.queue(tx=>executor.transaction(tx,async()=>{
        const before=await loadFacts(tx),facts=buildFixture(name,businessToday(now(),zone),zone);
        setMeta(facts,'data_revision',String(Number(before.app_meta.find(row=>row.key==='data_revision')?.value||0)+1));
        await persist(tx,before,facts);
      }));
      const snapshot=await context.refresh(true);
      if(!snapshot) throw new Error('REFRESH_FAILED');
      return {contextId,name,zone,today:snapshot.today,counts:Object.fromEntries(Object.entries(snapshot.facts).map(([table,rows])=>[table,rows.length])),dataRevision:snapshot.dataRevision};
    }
    case 'fault': {
      if(![null,'before_commit','after_commit'].includes(payload.point as null|string)) throw new Error('INVALID_FAULT_POINT');
      injectFault(payload.point as null|'before_commit'|'after_commit');
      return {contextId,point:payload.point};
    }
    case 'navigate': {
      if(typeof payload.route!=='string'||!/^\/(?:native|settings|\(tabs\)\/(?:today|plans|calendar)|plans\/new|plans\/[0-9a-f-]{36}(?:\/edit|\/calendar)?|records\/new|records\/[0-9a-f-]{36})$/.test(payload.route)) throw new Error('INVALID_TEST_ROUTE');
      const params=payload.params;
      if(params!==undefined&&(typeof params!=='object'||params===null||Array.isArray(params)||Object.entries(params).some(([key,value])=>!['planId','recordId','date','outcome'].includes(key)||typeof value!=='string'))) throw new Error('INVALID_ROUTE_PARAMS');
      router.replace({pathname:payload.route,params:params as Record<string,string>|undefined} as Parameters<typeof router.replace>[0]);
      return {contextId,route:payload.route,clock:now()};
    }
    case 'command': {
      const result=await context.service.execute(payload.envelope as Envelope);
      await context.refresh();
      return {contextId,result};
    }
    case 'sqlCase': {
      if(typeof payload.name!=='string')throw new Error('INVALID_SQL_CASE');
      return {contextId,observation:await runSqlCase(payload.name)};
    }
    case 'connectionInfo': return {contextId,observation:await connectionInfo()};
    case 'initializationProbe': {
      if(payload.confirm!=='CLOSE_ISOLATED_DEV_CONNECTION'||typeof payload.kind!=='string')throw new Error('INITIALIZATION_PROBE_CONFIRMATION_REQUIRED');
      return {contextId,observation:await initializationProbe(payload.kind)};
    }
    default: throw new Error('UNSUPPORTED_VERIFICATION_ACTION');
  }
}

function connect(){
  reconnect=undefined;
  requireIsolated();
  socket=new WebSocket('ws://127.0.0.1:8097/plancheckin-verification');
  const current=socket;
  current.onopen=()=>current.send(JSON.stringify({type:'hello',contextId,applicationId:Application.applicationId,api:Platform.Version,protocol:1,capabilities:['capture','clock','fixture','fault','navigate','command','sqlCase','connectionInfo','initializationProbe']}));
  current.onmessage=event=>{
    pending=pending.then(async()=>{
      let request:Request|undefined;
      try {
        if(typeof event.data!=='string'||event.data.length>100000) throw new Error('INVALID_REQUEST');
        request=JSON.parse(event.data) as Request;
        if(typeof request?.id!=='string'||request.id.length>80||typeof request.action!=='string') throw new Error('INVALID_REQUEST');
        const result=await dispatch(request);
        if(current.readyState===WebSocket.OPEN) current.send(JSON.stringify({id:request.id,ok:true,result}));
      } catch(error){
        if(current.readyState===WebSocket.OPEN) current.send(JSON.stringify({id:request?.id,ok:false,error:error instanceof Error?error.message:String(error)}));
      }
    });
  };
  current.onerror=()=>{};
  current.onclose=()=>{
    if(socket===current){socket=undefined;reconnect=setTimeout(connect,2000);}
  };
}

// Loaded only by the development Metro entry; the signed production bundle excludes this module.
export function startVerificationBridge(value:Context){
  if(!__DEV__||Application.applicationId!==applicationId) return;
  context=value;
  if(!socket&&!reconnect) connect();
}
