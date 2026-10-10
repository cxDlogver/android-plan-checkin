import { DateTime } from 'luxon';
import { addDays, dayMs, monday } from '../domain/date';
import { applyCommand, normalizeEnvelope } from '../domain/commands';
import { CommandKind, Envelope, Facts, emptyFacts, setMeta } from '../domain/model';
export const fixtureNames=['F01','F02','F03','F04','F05','F06','F07','F08','PERF'] as const;
export type FixtureName=typeof fixtureNames[number];
export const fixtureVersion=2;
export function fixtureSeed(name:FixtureName,today:string,zone:string){return `plancheckin-v${fixtureVersion}:${name}:${today}:${zone}`;}
export function buildFixture(name:FixtureName,today:string,zone:string,seed=fixtureSeed(name,today,zone)):Facts {
  let hash=2166136261,counter=0;for(const character of seed)hash=Math.imul(hash^character.charCodeAt(0),16777619);
  const prefix=(hash>>>0).toString(16).padStart(8,'0');
  const newId=()=>`${prefix}-0000-4000-8000-${(++counter).toString(16).padStart(12,'0')}`;
  let facts=emptyFacts();setMeta(facts,'app_timezone',zone);setMeta(facts,'initialized_at_ms',String(dayMs(today,zone)));setMeta(facts,'data_revision','0');
  const shift=(n:number)=>addDays(today,n,zone);
  function command(kind:CommandKind,payload:Record<string,unknown>,on:string){const instant=dayMs(on,zone)+12*3600000;const envelope:Envelope={commandId:newId(),issuedAtMs:instant,kind,payload};facts=applyCommand(facts,normalizeEnvelope(envelope),instant,zone,newId).facts;}
  const revision=(id:string)=>facts.plans.find(p=>p.id===id)!.revision;
  function create(type:'fixed'|'weekly'|'one_time',on:string,options:Record<string,unknown>={}){const planId=newId();command('CreatePlan',{planId,name:`${name} ${type}`,description:'隔离开发验收夹具',type,direction:'do',...(type==='one_time'?{dueOn:today}:{startsOn:on,endOn:null,...(type==='fixed'?{weekdayMask:127}:{weeklyTarget:3})}),...options},on);return planId;}
  function record(planId:string,on:string,result='success',note=''){command('SubmitCycleRecord',{planId,expectedPlanRevision:revision(planId),recordId:newId(),businessOn:on,result,note,confirmedToday:on,confirmedEntryKind:'ordinary'},on);}
  function manage(planId:string,kind:'RequestPause'|'RequestResume',on:string){command(kind,{planId,expectedPlanRevision:revision(planId),eventId:newId(),confirmedEffectiveOn:addDays(on,1,zone)},on);}
  if(name==='F03'){const id=create('fixed',shift(-8));for(let n=-8;n<0;n++)record(id,shift(n),n<-2?'success':'failure');}
  else if(name==='F02'){const id=create('fixed',shift(-20));record(id,shift(-9));manage(id,'RequestPause',shift(-8));manage(id,'RequestResume',shift(-4));}
  else if(name==='F04'){const start=addDays(monday(today,zone),-21,zone),id=create('weekly',start);for(let n=0;n<3;n++)record(id,addDays(start,n,zone));manage(id,'RequestPause',addDays(start,6,zone));manage(id,'RequestResume',addDays(start,13,zone));for(let n=14;n<17;n++)record(id,addDays(start,n,zone));}
  else if(name==='F05'){for(let n=0;n<100;n++){const id=create('fixed',shift(-1),{name:`日历 ${String(n+1).padStart(3,'0')}`});if(n<99)record(id,shift(-1));}}
  else if(name==='F07'){const id=create('fixed',today,{name:'长'.repeat(80),description:'说明'.repeat(500)});record(id,today,'failure','备注'.repeat(1000));}
  else if(name==='PERF'){
    const start=DateTime.fromISO(today,{zone}).minus({years:3}).toISODate()!,days=DateTime.fromISO(today,{zone}).diff(DateTime.fromISO(start,{zone}),'days').days;
    for(let n=0;n<100;n++){
      const id=create(n<40?'fixed':n<80?'weekly':'one_time',start,{name:`性能 ${String(n+1).padStart(3,'0')}`});
      if(n<80)for(let d=0;d<125;d++){const on=addDays(start,Math.floor(d*(days-1)/124),zone);facts.cycle_records.push({id:newId(),plan_id:id,business_on:on,result:d%7===0?'skip':d%3===0?'failure':'success',note:'性能夹具',entry_kind:'ordinary',submitted_at_ms:dayMs(on,zone)+3600000,modified_at_ms:null,revision:1});}
      else if(n<90){const on=shift(-30-(n-80));command('SubmitOneTimeResult',{planId:id,expectedPlanRevision:revision(id),resultId:newId(),outcome:'completed',actualCompletedOn:on,note:'性能夹具',confirmedToday:on,confirmedEntryKind:'ordinary'},on);}
    }
  }
  else {create('fixed',today);create('weekly',today);create('one_time',today);create('fixed',today,{direction:'avoid',name:`${name} 不要做`});}
  return facts;
}
