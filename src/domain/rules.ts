import { addDays, dayMs, daysBetween, monday, weekday } from './date';
import { BusinessDate, CycleRecord, Facts, LifecycleEvent, OneTimeResult, Plan, Rule, RuleKind, Snapshot, Status } from './model';

export function resolveRule(facts: Facts,planId: string,kind: RuleKind,on: BusinessDate): Rule | undefined {
  return facts.rule_versions.filter(rule=>rule.plan_id===planId&&rule.kind===kind&&rule.cancelled_at_ms===null&&rule.effective_on<=on).sort((a,b)=>b.effective_on.localeCompare(a.effective_on)||b.revision-a.revision)[0];
}
export function ruleValue<T>(facts: Facts,planId: string,kind: RuleKind,on: BusinessDate): T {
  const rule=resolveRule(facts,planId,kind,on);return rule?Object.values(JSON.parse(rule.value_json))[0] as T:undefined as T;
}
export const pendingRules=(facts:Facts,planId:string,today:string)=>facts.rule_versions.filter(rule=>rule.plan_id===planId&&rule.cancelled_at_ms===null&&rule.effective_on>today);
export function events(facts:Facts,planId:string){return facts.lifecycle_events.filter(event=>event.plan_id===planId&&event.cancelled_at_ms===null).sort((a,b)=>a.effective_at_ms-b.effective_at_ms||(a.kind==='archive'?-1:b.kind==='archive'?1:0)||a.id.localeCompare(b.id));}
export function archiveEvent(facts:Facts,planId:string,now:number){return events(facts,planId).find(event=>event.kind==='archive'&&event.effective_at_ms<=now);}
export function status(facts:Facts,planId:string,now:number):Status {let value:Status='running';for(const event of events(facts,planId)){if(event.effective_at_ms>now)break;if(event.kind==='archive')return 'archived';value=event.kind==='pause'?'paused':'running';}return value;}
export const pendingState=(facts:Facts,planId:string,now:number)=>events(facts,planId).find(event=>event.kind!=='archive'&&event.effective_at_ms>now);
export interface Interval { start: number; end: number }
export function intervals(facts:Facts,plan:Plan,zone:string):Interval[]{
  const starts=dayMs(plan.starts_on,zone),endOn=ruleValue<string|null>(facts,plan.id,'end_on','9999-12-31');
  const limit=endOn?dayMs(addDays(endOn,1,zone),zone):Infinity;
  let start:number|null=starts;const result:Interval[]=[];
  for(const event of events(facts,plan.id)){
    const end=Math.min(event.effective_at_ms,limit);
    if(event.kind==='pause'||event.kind==='archive'){if(start!==null&&end>start)result.push({start,end});start=null;}
    if(event.kind==='resume')start=Math.max(starts,event.effective_at_ms);
    if(event.kind==='archive')break;
  }
  if(start!==null&&limit>start)result.push({start,end:limit});return result;
}
export function eligibleOn(facts:Facts,plan:Plan,on:string,zone:string){
  if(plan.type==='one_time'||on<plan.starts_on)return false;
  const endOn=ruleValue<string|null>(facts,plan.id,'end_on',on);if(endOn&&on>endOn)return false;
  const at=dayMs(on,zone);if(!intervals(facts,plan,zone).some(stage=>stage.start<=at&&stage.end>at))return false;
  if(events(facts,plan.id).some(e=>e.kind==='archive'&&e.reason==='user'&&on>=e.effective_on))return false;
  return plan.type==='weekly'||!!(ruleValue<number>(facts,plan.id,'weekday_mask',on)&(1<<(weekday(on,zone)-1)));
}
export function permission(snapshot:Snapshot,plan:Plan,on:string,record?:CycleRecord|OneTimeResult): {allowed:boolean;reason?:string;entryKind?:'ordinary'|'backfill'} {
  const {facts,today,asOfMs,zone}=snapshot;const state=status(facts,plan.id,asOfMs);
  if(state==='archived')return {allowed:false,reason:'ARCHIVED'};
  if(state==='paused')return {allowed:false,reason:'PAUSED'};
  if(record)return record.entry_kind==='ordinary'&&record.business_on===today?{allowed:true,entryKind:'ordinary'}:{allowed:false,reason:'READ_ONLY'};
  if(on>today||on<plan.created_on)return {allowed:false,reason:'DATE_INELIGIBLE'};
  if(plan.type==='one_time')return {allowed:true,entryKind:on===today?'ordinary':'backfill'};
  if(!eligibleOn(facts,plan,on,zone))return {allowed:false,reason:'DATE_INELIGIBLE'};
  const current=intervals(facts,plan,zone).find(stage=>stage.start<=asOfMs&&stage.end>asOfMs);
  if(!current||dayMs(on,zone)<current.start)return {allowed:false,reason:'OLD_STAGE'};
  return {allowed:true,entryKind:on===today?'ordinary':'backfill'};
}
export interface CalendarItem { key:string; plan:Plan; on:string; record?:CycleRecord|OneTimeResult; completed:boolean }
export function dailyItems(snapshot:Snapshot,on:string,planId?:string):CalendarItem[]{
  const {facts,zone}=snapshot;const result:CalendarItem[]=[];
  for(const plan of facts.plans){if(planId&&plan.id!==planId)continue;
    const record=plan.type==='one_time'?facts.one_time_results.find(item=>item.plan_id===plan.id):facts.cycle_records.find(item=>item.plan_id===plan.id&&item.business_on===on);
    if(record){if(record.business_on===on)result.push({key:`${plan.id}:${on}`,plan,on,record,completed:'result' in record?record.result==='success':record.outcome==='completed'});continue;}
    if(plan.type==='one_time'){
      const due=ruleValue<string>(facts,plan.id,'due_on',snapshot.today),archived=archiveEvent(facts,plan.id,snapshot.asOfMs);
      if(due===on&&(!archived||due<archived.effective_on))result.push({key:`${plan.id}:${on}`,plan,on,completed:false});
    }else if(plan.type==='fixed'&&eligibleOn(facts,plan,on,zone))result.push({key:`${plan.id}:${on}`,plan,on,completed:false});
  }return result.sort((a,b)=>a.plan.created_at_ms-b.plan.created_at_ms||a.plan.id.localeCompare(b.plan.id));
}
export function marker(items:CalendarItem[],on:string,today:string){const completed=items.filter(item=>item.completed).length,total=items.length;return {completed,total,label:on===today||total===0?'':completed===total?'✓':`${completed}/${total}`};}
export function displayPeriod(snapshot:Snapshot,plan:Plan){const arch=archiveEvent(snapshot.facts,plan.id,snapshot.asOfMs);const until=arch?.reason==='cycle_end'?addDays(arch.effective_on,-1,snapshot.zone):arch?.effective_on||snapshot.today;const first=plan.type==='one_time'?plan.created_on:plan.starts_on;return {kind:first>until?(arch?'no_execution':'not_started'):'range',startsOn:first,until,archivedOn:arch?.effective_on};}
export function fixedStatistics(snapshot:Snapshot,plan:Plan){
  const period=displayPeriod(snapshot,plan);let numerator=0,denominator=0,skipCount=0,pastUnknownCount=0,currentStreak=0,maximumStreak=0,lastStage:number|undefined;
  if(period.kind==='range')for(const on of daysBetween(period.startsOn,period.until,snapshot.zone)){
    const record=snapshot.facts.cycle_records.find(item=>item.plan_id===plan.id&&item.business_on===on);if(!record&&!eligibleOn(snapshot.facts,plan,on,snapshot.zone))continue;
    const stage=intervals(snapshot.facts,plan,snapshot.zone).find(item=>item.start<=dayMs(on,snapshot.zone)&&item.end>dayMs(on,snapshot.zone));
    if(lastStage!==undefined&&stage?.start!==lastStage)currentStreak=0;lastStage=stage?.start;
    if(on>snapshot.today||on===snapshot.today&&!record)continue;
    if(record?.result==='skip')skipCount++;else denominator++;
    if(record?.result==='success'){numerator++;currentStreak++;maximumStreak=Math.max(maximumStreak,currentStreak);}else {currentStreak=0;if(!record&&on<snapshot.today)pastUnknownCount++;}
  }
  const activeStage=intervals(snapshot.facts,plan,snapshot.zone).find(item=>item.start<=snapshot.asOfMs&&item.end>snapshot.asOfMs);
  if(status(snapshot.facts,plan.id,snapshot.asOfMs)==='paused'||activeStage&&lastStage!==undefined&&activeStage.start!==lastStage)currentStreak=0;
  return {period,numerator,denominator,rate:denominator?numerator/denominator:null,skipCount,pastUnknownCount,currentStreak,maximumStreak};
}
export function weeklyStatistics(snapshot:Snapshot,plan:Plan){
  const period=displayPeriod(snapshot,plan),stages=intervals(snapshot.facts,plan,snapshot.zone);let numerator=0,denominator=0,currentStreak=0,maximumStreak=0;const weeks=[];
  const first=monday(plan.starts_on,snapshot.zone),last=monday(snapshot.today,snapshot.zone);
  for(let start=first;start<=last;start=addDays(start,7,snapshot.zone)){
    const end=addDays(start,7,snapshot.zone),a=dayMs(start,snapshot.zone),b=dayMs(end,snapshot.zone),target=ruleValue<number>(snapshot.facts,plan.id,'weekly_target',start)||ruleValue<number>(snapshot.facts,plan.id,'weekly_target',snapshot.today);
    const success=new Set(snapshot.facts.cycle_records.filter(r=>r.plan_id===plan.id&&r.result==='success'&&r.business_on>=start&&r.business_on<end).map(r=>r.business_on)).size;
    const fullEligible=stages.some(stage=>stage.start<=a&&stage.end>=b),ended=b<=snapshot.asOfMs;
    const archived=archiveEvent(snapshot.facts,plan.id,snapshot.asOfMs),hasExecution=stages.some(stage=>stage.start<b&&stage.end>a);
    if(ended){if(fullEligible&&end<=addDays(period.until,1,snapshot.zone)){denominator++;if(success>=target)numerator++;}if(fullEligible&&success>=target){currentStreak++;maximumStreak=Math.max(maximumStreak,currentStreak);}else if(start<=period.until&&(hasExecution||start>=plan.starts_on))currentStreak=0;}
    weeks.push({start,end,target,success,fullEligible,ended,progress:Math.min(1,success/target),partialReason:fullEligible?null:hasExecution?'部分周':'暂停周',frozen:!!archived});
  }
  return {period,numerator,denominator,rate:denominator?numerator/denominator:null,currentStreak,maximumStreak,current:weeks.find(week=>week.start===monday(snapshot.today,snapshot.zone)),weeks};
}
export const isOnTime=(result:OneTimeResult,rule:Rule)=>result.outcome==='completed'&&result.business_on<=JSON.parse(rule.value_json).dueOn;
export function todaySections(snapshot:Snapshot){
  const ordered=[...snapshot.facts.plans].sort((a,b)=>a.created_at_ms-b.created_at_ms||a.id.localeCompare(b.id));
  const fixed:Plan[]=[],weekly:Plan[]=[],once:Plan[]=[],recorded:Plan[]=[];
  for(const plan of ordered){const record=plan.type==='one_time'?snapshot.facts.one_time_results.find(r=>r.plan_id===plan.id&&r.business_on===snapshot.today):snapshot.facts.cycle_records.find(r=>r.plan_id===plan.id&&r.business_on===snapshot.today);
    if(record){recorded.push(plan);continue;}if(status(snapshot.facts,plan.id,snapshot.asOfMs)!=='running')continue;
    if(plan.type==='one_time'){if(!snapshot.facts.one_time_results.some(r=>r.plan_id===plan.id))once.push(plan);}else if(permission(snapshot,plan,snapshot.today).allowed)(plan.type==='fixed'?fixed:weekly).push(plan);
  }
  once.sort((a,b)=>ruleValue<string>(snapshot.facts,a.id,'due_on',snapshot.today).localeCompare(ruleValue<string>(snapshot.facts,b.id,'due_on',snapshot.today))||a.created_at_ms-b.created_at_ms||a.id.localeCompare(b.id));return {fixed,weekly,once,recorded};
}
