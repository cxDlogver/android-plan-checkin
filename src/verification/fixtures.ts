import * as Crypto from 'expo-crypto';
import { addDays, dayMs, monday } from '../domain/date';
import { applyCommand, normalizeEnvelope } from '../domain/commands';
import { CommandKind, Envelope, Facts, emptyFacts, setMeta } from '../domain/model';
export const fixtureNames=['F01','F02','F03','F04','F05','F06','F07','F08','PERF'] as const;
export type FixtureName=typeof fixtureNames[number];
export function buildFixture(name:FixtureName,today:string,zone:string):Facts {
  let facts=emptyFacts();setMeta(facts,'app_timezone',zone);setMeta(facts,'initialized_at_ms',String(dayMs(today,zone)));setMeta(facts,'data_revision','0');
  const shift=(n:number)=>addDays(today,n,zone);
  function command(kind:CommandKind,payload:Record<string,unknown>,on:string){const instant=dayMs(on,zone)+12*3600000;const envelope:Envelope={commandId:Crypto.randomUUID(),issuedAtMs:instant,kind,payload};facts=applyCommand(facts,normalizeEnvelope(envelope),instant,zone,Crypto.randomUUID).facts;}
  const revision=(id:string)=>facts.plans.find(p=>p.id===id)!.revision;
  function create(type:'fixed'|'weekly'|'one_time',on:string,options:Record<string,unknown>={}){const planId=Crypto.randomUUID();command('CreatePlan',{planId,name:`${name} ${type}`,description:'隔离开发验收夹具',type,direction:'do',...(type==='one_time'?{dueOn:today}:{startsOn:on,endOn:null,...(type==='fixed'?{weekdayMask:127}:{weeklyTarget:3})}),...options},on);return planId;}
  function record(planId:string,on:string,result='success',note=''){command('SubmitCycleRecord',{planId,expectedPlanRevision:revision(planId),recordId:Crypto.randomUUID(),businessOn:on,result,note,confirmedToday:on,confirmedEntryKind:'ordinary'},on);}
  function manage(planId:string,kind:'RequestPause'|'RequestResume',on:string){command(kind,{planId,expectedPlanRevision:revision(planId),eventId:Crypto.randomUUID(),confirmedEffectiveOn:addDays(on,1,zone)},on);}
  if(name==='F03'){const id=create('fixed',shift(-8));for(let n=-8;n<0;n++)record(id,shift(n),n<-2?'success':'failure');}
  else if(name==='F02'){const id=create('fixed',shift(-20));record(id,shift(-9));manage(id,'RequestPause',shift(-8));manage(id,'RequestResume',shift(-4));}
  else if(name==='F04'){const start=addDays(monday(today,zone),-21,zone),id=create('weekly',start);for(let n=0;n<3;n++)record(id,addDays(start,n,zone));manage(id,'RequestPause',addDays(start,6,zone));manage(id,'RequestResume',addDays(start,13,zone));for(let n=14;n<17;n++)record(id,addDays(start,n,zone));}
  else if(name==='F05'){for(let n=0;n<100;n++){const id=create('fixed',shift(-1),{name:`日历 ${String(n+1).padStart(3,'0')}`});if(n<99)record(id,shift(-1));}}
  else if(name==='F07'){const id=create('fixed',today,{name:'长'.repeat(80),description:'说明'.repeat(500)});record(id,today,'failure','备注'.repeat(1000));}
  else if(name==='PERF'){
    const start=shift(-100);
    for(let n=0;n<100;n++){const id=create('fixed',start,{name:`性能 ${n+1}`});for(let d=-100;d<0;d++)facts.cycle_records.push({id:Crypto.randomUUID(),plan_id:id,business_on:shift(d),result:d%7===0?'skip':d%3===0?'failure':'success',note:'性能夹具',entry_kind:'ordinary',submitted_at_ms:dayMs(shift(d),zone)+3600000,modified_at_ms:null,revision:1});}
  }
  else {create('fixed',today);create('weekly',today);create('one_time',today);create('fixed',today,{direction:'avoid',name:`${name} 不要做`});}
  return facts;
}
