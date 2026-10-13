import { Facts, CycleRecord, DomainError, OneTimeResult, Plan, Snapshot, Status } from '../domain/model';
import { monthGrid } from '../domain/date';
import { archiveEvent, dailyItems, fixedStatistics, marker, pendingRules, pendingState, permission, status, todaySections, weeklyStatistics } from '../domain/rules';

export interface Header { asOfMs:number; today:string; zone:string; dataRevision:number }
export interface Cursor { scope:string; today:string; zone:string; dataRevision:number; tuple:(string|number)[] }
export interface PageResult<T> extends Header { items:T[]; nextCursor:Cursor|null; reset:boolean }
const header=(s:Snapshot):Header=>({asOfMs:s.asOfMs,today:s.today,zone:s.zone,dataRevision:s.dataRevision});
const identity=(s:Snapshot)=>`${s.today}|${s.zone}|${s.dataRevision}`;
const same=(s:Snapshot,c:Cursor,scope:string)=>c.scope===scope&&c.today===s.today&&c.zone===s.zone&&c.dataRevision===s.dataRevision;
function page<T>(s:Snapshot,scope:string,rows:T[],tuple:(row:T)=>(string|number)[],cursor?:Cursor|null,size=50):PageResult<T>{
  const reset=!!cursor&&!same(s,cursor,scope),limit=Math.min(100,Math.max(1,Math.trunc(size)||50));
  const found=cursor&&!reset?rows.findIndex(row=>JSON.stringify(tuple(row))===JSON.stringify(cursor.tuple)):-1;
  const start=found+1,items=rows.slice(start,start+limit),last=items.at(-1);
  return {...header(s),items,nextCursor:last&&start+limit<rows.length?{...header(s),scope,tuple:tuple(last)}:null,reset:reset||!!cursor&&found<0};
}
type RecordRow=CycleRecord|OneTimeResult;
export class Projections {
  private version='';
  private scoped=new Map<string,Facts>();
  private facts:Facts|null=null;
  private group<T extends {plan_id:string}>(rows:T[]){const map=new Map<string,T[]>();for(const row of rows){const values=map.get(row.plan_id)||[];values.push(row);map.set(row.plan_id,values);}return map;}
  private view(s:Snapshot,plan:Plan):Snapshot{return {...s,facts:this.scoped.get(plan.id)!};}
  private months=new Map<string,ReturnType<typeof this.monthValue>>();
  private details=new Map<string,ReturnType<typeof this.detailValue>>();
  invalidate(){this.version='';this.facts=null;this.scoped.clear();this.months.clear();this.details.clear();}
  private prepare(s:Snapshot){if(identity(s)!==this.version||this.facts!==s.facts){this.invalidate();this.version=identity(s);this.facts=s.facts;const rules=this.group(s.facts.rule_versions),events=this.group(s.facts.lifecycle_events),cycles=this.group(s.facts.cycle_records),once=this.group(s.facts.one_time_results);for(const plan of s.facts.plans)this.scoped.set(plan.id,{...s.facts,plans:[plan],rule_versions:rules.get(plan.id)||[],lifecycle_events:events.get(plan.id)||[],cycle_records:cycles.get(plan.id)||[],one_time_results:once.get(plan.id)||[]});}}
  private bounded<T>(cache:Map<string,T>,key:string,limit:number,compute:()=>T):T {
    const value=cache.get(key)??compute();cache.delete(key);cache.set(key,value);
    if(cache.size>limit)cache.delete(cache.keys().next().value!);
    return value;
  }
  today(s:Snapshot){return {...header(s),sections:todaySections(s)};}
  private items(s:Snapshot,on:string,planId?:string){return s.facts.plans.filter(p=>!planId||p.id===planId).flatMap(p=>dailyItems(this.view(s,p),on)).sort((a,b)=>a.plan.created_at_ms-b.plan.created_at_ms||a.plan.id.localeCompare(b.plan.id));}
  private monthValue(s:Snapshot,month:string,planId?:string){return monthGrid(month,s.zone).map(on=>({on,...marker(this.items(s,on,planId),on,s.today)}));}
  calendar(s:Snapshot,month:string,selectedDate:string,planId?:string){
    this.prepare(s);
    if(planId&&!s.facts.plans.some(p=>p.id===planId))throw new DomainError('TARGET_REMOVED');
    const days=this.bounded(this.months,`${planId||'*'}|${month}`,3,()=>this.monthValue(s,month,planId));
    const items=this.items(s,selectedDate,planId);
    const weeklyBackfills=selectedDate<s.today?s.facts.plans.filter(p=>(!planId||p.id===planId)&&p.type==='weekly'&&!s.facts.cycle_records.some(r=>r.plan_id===p.id&&r.business_on===selectedDate)&&permission(this.view(s,p),p,selectedDate).allowed):[];
    return {...header(s),month,selectedDate,days,items,weeklyBackfills};
  }
  plans(s:Snapshot,filter:Status,cursor?:Cursor|null,size=50){
    const rows=s.facts.plans.filter(p=>status(s.facts,p.id,s.asOfMs)===filter).sort((a,b)=>a.created_at_ms-b.created_at_ms||a.id.localeCompare(b.id));
    return page(s,`plans:${filter}`,rows,p=>[p.created_at_ms,p.id],cursor,size);
  }
  history(s:Snapshot,planId:string,cursor?:Cursor|null,size=50){
    const plan=s.facts.plans.find(p=>p.id===planId);if(!plan)throw new DomainError('TARGET_REMOVED');
    const records:RecordRow[]=(plan.type==='one_time'?s.facts.one_time_results:s.facts.cycle_records).filter(r=>r.plan_id===planId).sort((a,b)=>b.business_on.localeCompare(a.business_on)||b.id.localeCompare(a.id));
    return {...page(s,`history:${planId}`,records,r=>[r.business_on,r.id],cursor,size),total:records.length};
  }
  private detailValue(s:Snapshot,plan:Plan){return {plan,status:status(s.facts,plan.id,s.asOfMs),pendingState:pendingState(s.facts,plan.id,s.asOfMs),pendingRules:pendingRules(s.facts,plan.id,s.today),archive:archiveEvent(s.facts,plan.id,s.asOfMs),statistics:plan.type==='fixed'?fixedStatistics(s,plan):plan.type==='weekly'?weeklyStatistics(s,plan):null,todayPermission:permission(s,plan,s.today)};}
  detail(s:Snapshot,planId:string){
    this.prepare(s);const plan=s.facts.plans.find(p=>p.id===planId);if(!plan){this.details.delete(planId);throw new DomainError('TARGET_REMOVED');}
    return {...header(s),...this.bounded(this.details,planId,10,()=>this.detailValue(this.view(s,plan),plan))};
  }
  record(s:Snapshot,planId:string,recordId:string){
    const plan=s.facts.plans.find(p=>p.id===planId),record=s.facts.cycle_records.find(r=>r.id===recordId&&r.plan_id===planId)||s.facts.one_time_results.find(r=>r.id===recordId&&r.plan_id===planId);
    if(!plan||!record)throw new DomainError('TARGET_REMOVED');
    const original='result'in record?s.facts.cycle_record_originals.find(r=>r.record_id===record.id):s.facts.one_time_result_originals.find(r=>r.result_id===record.id);
    return {...header(s),plan,record,original,permission:permission(s,plan,record.business_on,record)};
  }
  settings(s:Snapshot,nativeVersion:string|null,nativeBuild:string|null){return {...header(s),nativeVersion:nativeVersion||'不可用',nativeBuild:nativeBuild||'不可用',offline:true,backup:false};}
}
