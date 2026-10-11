import { Dimensions, Platform } from 'react-native';
import * as Application from 'expo-application';
import * as Font from 'expo-font';
import { router } from 'expo-router';
import { DateTime } from 'luxon';
import type { AppService } from '../application/service';
import type { Envelope, Snapshot } from '../domain/model';
import { emptyFacts, Facts, setMeta } from '../domain/model';
import { businessToday, validZone } from '../domain/date';
import { loadFacts, persist } from '../infrastructure/database/executor';
import { buildFixture, fixtureNames, FixtureName } from './fixtures';
import { beginReadInitialization, injectFault, faultStatus, now, overrideSettingsVersion, setClock, verificationExecutor } from './runtime-development';
import { runSqlCase } from './sql-cases-development';
import { connectionInfo, initializationProbe } from './initialization-development';
import { migrationProbe, migrationStatus } from './migration-development';
import { migrationV2Probe } from './migration-v2-development';
import { calendarProbe, dateProbe, timezoneProbe } from './date-development';
import { Projections } from '../application/projections';
import { intervals, isOnTime, permission } from '../domain/rules';

type Context = { service:AppService; refresh:(clearPins?:boolean)=>Promise<Snapshot|undefined> };
type Request = { id:string; action:string; payload?:Record<string,unknown> };
const applicationId = 'com.xiang.plancheckin.dev';
const contextId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
let context:Context|undefined;
let socket:WebSocket|undefined;
let reconnect:ReturnType<typeof setTimeout>|undefined;
let pending:Promise<unknown> = Promise.resolve();
const queries=new Projections();

function requireIsolated(){
  if(!__DEV__||Application.applicationId!==applicationId) throw new Error('ISOLATED_DEVELOPMENT_ONLY');
}
async function dispatch({action,payload={}}:Request){
  requireIsolated();
  if(!context) throw new Error('APPLICATION_NOT_READY');
  switch(action){
    case 'capture': {
      const snapshot=await context.service.snapshot();
      return {contextId,applicationId:Application.applicationId,api:Platform.Version,nativeVersion:Application.nativeApplicationVersion,nativeBuild:Application.nativeBuildVersion,window:Dimensions.get('window'),clock:now(),sqlite:await context.service.diagnostics(),fonts:['NotoSC400','NotoSC600','NotoSC700'].map(name=>({name,loaded:Font.isLoaded(name)})),snapshot};
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
      queries.invalidate();
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
      queries.invalidate();
      const snapshot=await context.refresh(true);
      if(!snapshot) throw new Error('REFRESH_FAILED');
      return {contextId,name,zone,today:snapshot.today,counts:Object.fromEntries(Object.entries(snapshot.facts).map(([table,rows])=>[table,rows.length])),dataRevision:snapshot.dataRevision};
    }
    case 'factsFixture': {
      if(payload.confirm!=='RESET_ISOLATED_DEV_FACTS'||typeof payload.facts!=='object'||payload.facts===null)throw new Error('FACTS_FIXTURE_CONFIRMATION_REQUIRED');
      const facts=payload.facts as Facts;
      const tables=Object.keys(emptyFacts()).sort();
      if(JSON.stringify(Object.keys(facts).sort())!==JSON.stringify(tables)||tables.some(table=>!Array.isArray(facts[table as keyof Facts])))throw new Error('INVALID_FACTS_FIXTURE');
      const zone=facts.app_meta.find(row=>row.key==='app_timezone')?.value;
      if(!zone||!validZone(zone))throw new Error('INVALID_FACTS_ZONE');
      injectFault(null);const executor=verificationExecutor();
      await executor.queue(tx=>executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),facts)));
      queries.invalidate();
      const snapshot=await context.refresh(true);if(!snapshot)throw new Error('REFRESH_FAILED');
      return {contextId,today:snapshot.today,zone:snapshot.zone,counts:Object.fromEntries(Object.entries(snapshot.facts).map(([table,rows])=>[table,rows.length])),dataRevision:snapshot.dataRevision};
    }
    case 'refresh': return {contextId,refreshed:!!await context.refresh()};
    case 'readInitialization': beginReadInitialization();return {contextId,started:true};
    case 'settingsVersion': {
      if(![null,'native'].includes(payload.mode as null|string))throw new Error('INVALID_VERSION_PROBE');
      overrideSettingsVersion(payload.mode===null?{version:null,build:null}:undefined);await context.refresh();return {contextId,mode:payload.mode};
    }
    case 'faultStatus': return {contextId,...faultStatus()};
    case 'fault': {
      if(![null,'before_commit','before_commit_io','before_commit_busy','after_commit','before_commit_hold','after_commit_hold','read_io','read_hold'].includes(payload.point as null|string)) throw new Error('INVALID_FAULT_POINT');
      injectFault(payload.point as Parameters<typeof injectFault>[0]);
      return {contextId,point:payload.point};
    }
    case 'navigate': {
      if(typeof payload.route!=='string'||!/^\/(?:native|settings|\(tabs\)\/(?:today|plans|calendar)|plans\/new|plans\/[0-9a-f-]{36}(?:\/edit|\/calendar)?|records\/new|records\/[0-9a-f-]{36})$/.test(payload.route)) throw new Error('INVALID_TEST_ROUTE');
      const params=payload.params;
      if(params!==undefined&&(typeof params!=='object'||params===null||Array.isArray(params)||Object.entries(params).some(([key,value])=>!['planId','recordId','date','outcome','businessOn','result'].includes(key)||typeof value!=='string'))) throw new Error('INVALID_ROUTE_PARAMS');
      if(payload.mode!==undefined&&!['push','replace'].includes(payload.mode as string))throw new Error('INVALID_NAVIGATION_MODE');
      const destination={pathname:payload.route,params:params as Record<string,string>|undefined} as Parameters<typeof router.replace>[0];
      if(payload.mode==='push')router.push(destination);else router.replace(destination);
      return {contextId,route:payload.route,clock:now()};
    }
    case 'command': {
      const result=await context.service.execute(payload.envelope as Envelope);
      if(payload.refresh!==false)await context.refresh();
      return {contextId,result};
    }
    case 'query': {
      const snapshot=await context.service.snapshot();
      const planId=typeof payload.planId==='string'?payload.planId:undefined;
      const on=typeof payload.on==='string'?payload.on:snapshot.today;
      switch(payload.kind){
        case 'today': return {contextId,view:queries.today(snapshot)};
        case 'calendar': return {contextId,view:queries.calendar(snapshot,typeof payload.month==='string'?payload.month:on.slice(0,7),on,planId)};
        case 'detail': if(!planId)throw new Error('PLAN_REQUIRED');return {contextId,view:queries.detail(snapshot,planId)};
        case 'history': if(!planId)throw new Error('PLAN_REQUIRED');return {contextId,view:queries.history(snapshot,planId,payload.cursor as Parameters<Projections['history']>[2],Number(payload.size)||50)};
        case 'classification': {
          const record=snapshot.facts.one_time_results.find(r=>r.plan_id===planId&&r.id===payload.recordId);
          const rule=snapshot.facts.rule_versions.find(r=>r.id===record?.due_rule_version_id);
          if(!record||!rule)throw new Error('RECORD_REQUIRED');
          return {contextId,view:{onTime:isOnTime(record,rule),outcome:record.outcome,businessOn:record.business_on,rule}};
        }
        case 'plans': if(!['running','paused','archived'].includes(payload.filter as string))throw new Error('INVALID_QUERY_FILTER');return {contextId,view:queries.plans(snapshot,payload.filter as Parameters<Projections['plans']>[1],payload.cursor as Parameters<Projections['plans']>[2],Number(payload.size)||50)};
        case 'permission': {
          const plan=snapshot.facts.plans.find(p=>p.id===planId);if(!plan)throw new Error('PLAN_REQUIRED');
          const record=snapshot.facts.cycle_records.find(r=>r.id===payload.recordId&&r.plan_id===planId)||snapshot.facts.one_time_results.find(r=>r.id===payload.recordId&&r.plan_id===planId);
          return {contextId,view:{today:snapshot.today,zone:snapshot.zone,dataRevision:snapshot.dataRevision,permission:permission(snapshot,plan,on,record),intervals:intervals(snapshot.facts,plan,snapshot.zone)}};
        }
        default: throw new Error('INVALID_QUERY_KIND');
      }
    }
    case 'cleanReceipts': await context.service.cleanReceipts();return {contextId,cleaned:true};
    case 'sqlCase': {
      if(typeof payload.name!=='string')throw new Error('INVALID_SQL_CASE');
      return {contextId,observation:await runSqlCase(payload.name)};
    }
    case 'connectionInfo': return {contextId,observation:await connectionInfo()};
    case 'storageCapacity': {
      if(payload.confirm!=='TRUNCATE_ISOLATED_DEV_WAL')throw new Error('CAPACITY_PROBE_CONFIRMATION_REQUIRED');
      const observation=await verificationExecutor().queue(async tx=>({checkpoint:await tx.first('PRAGMA wal_checkpoint(TRUNCATE)'),pageCount:await tx.first('PRAGMA page_count'),freelist:await tx.first('PRAGMA freelist_count')}));
      return {contextId,observation};
    }
    case 'dateProbe': return {contextId,observation:dateProbe()};
    case 'calendarProbe': return {contextId,observation:calendarProbe(await context.service.snapshot())};
    case 'timezoneProbe': {
      if(payload.confirm!=='INITIALIZE_ISOLATED_DEV_TIMEZONE'||!['Asia/Shanghai','Invalid/Zone',null].includes(payload.candidate as string|null)||typeof payload.empty!=='boolean')throw new Error('TIMEZONE_PROBE_CONFIRMATION_REQUIRED');
      return {contextId,observation:await timezoneProbe(payload.candidate as string|null,payload.empty)};
    }
    case 'migrationStatus': return {contextId,observation:migrationStatus()};
    case 'migrationV2Probe': {
      if(payload.confirm!=='MIGRATE_ISOLATED_DEV_DATABASE')throw new Error('MIGRATION_PROBE_CONFIRMATION_REQUIRED');
      return {contextId,observation:await migrationV2Probe()};
    }
    case 'migrationProbe': {
      if(payload.confirm!=='MIGRATE_ISOLATED_DEV_DATABASE'||typeof payload.kind!=='string')throw new Error('MIGRATION_PROBE_CONFIRMATION_REQUIRED');
      return {contextId,observation:await migrationProbe(payload.kind)};
    }
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
  current.onopen=()=>current.send(JSON.stringify({type:'hello',contextId,applicationId:Application.applicationId,api:Platform.Version,protocol:1,capabilities:['capture','clock','fixture','fault','navigate','command','sqlCase','connectionInfo','initializationProbe','migrationProbe','migrationStatus','dateProbe','timezoneProbe','calendarProbe']}));
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
