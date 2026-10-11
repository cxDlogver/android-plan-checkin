import { z } from 'zod';
import { addDays, businessToday, date, dayMs, nextMonday } from './date';
import { archiveEvent, events, pendingState, permission, resolveRule, ruleValue, status } from './rules';
import { CycleRecord, DomainError, Envelope, Facts, LifecycleEvent, Plan, Receipt, RuleKind, Snapshot, setMeta, metaValue } from './model';

const id=z.uuid(),day=z.string().regex(/^\d{4}-\d{2}-\d{2}$/),positive=z.number().int().positive();
const text=(maximum:number,required=false)=>z.string().refine(value=>[...value].length<=maximum&&(!required||value.trim().length>0));
const planRef={planId:id,expectedPlanRevision:positive};
const confirmation={confirmedToday:day,confirmedEntryKind:z.enum(['ordinary','backfill'])};
const note=text(2000);
const name=text(80,true).refine(value=>!/[\r\n\u2028\u2029]/.test(value),'名称只能为单行');
const create=z.object({planId:id,name,description:text(1000),type:z.enum(['fixed','weekly','one_time']),direction:z.enum(['do','avoid']),startsOn:day.optional(),weekdayMask:z.number().int().min(1).max(127).optional(),weeklyTarget:z.number().int().min(1).max(7).optional(),endOn:day.nullable().optional(),dueOn:day.optional()}).strict();
const payloads={
  CreatePlan:create,
  SubmitCycleRecord:z.object({...planRef,...confirmation,recordId:id,businessOn:day,result:z.enum(['success','failure','skip']),note}).strict(),
  ModifyCycleRecord:z.object({...planRef,recordId:id,expectedRecordRevision:positive,result:z.enum(['success','failure','skip']),note}).strict(),
  SubmitOneTimeResult:z.object({...planRef,...confirmation,resultId:id,outcome:z.enum(['completed','failed','cancelled']),actualCompletedOn:day.nullable(),note}).strict(),
  ModifyOneTimeResult:z.object({...planRef,resultId:id,expectedRecordRevision:positive,outcome:z.enum(['completed','failed','cancelled']),note}).strict(),
  EditPlan:z.object({...planRef,changes:z.object({name:name.optional(),description:text(1000).optional(),weekdayMask:z.number().int().min(1).max(127).optional(),weeklyTarget:z.number().int().min(1).max(7).optional(),endOn:day.nullable().optional(),dueOn:day.optional()}).strict(),ruleConfirmations:z.array(z.object({field:z.enum(['weekday_mask','weekly_target']),confirmedEffectiveOn:day}).strict())}).strict(),
  RequestPause:z.object({...planRef,eventId:id,confirmedEffectiveOn:day}).strict(),
  RequestResume:z.object({...planRef,eventId:id,confirmedEffectiveOn:day}).strict(),
  CancelPendingState:z.object({...planRef,eventId:id}).strict(),
  ArchivePlan:z.object({...planRef,eventId:id}).strict(),
  PermanentlyDeletePlan:z.object(planRef).strict(),
};
export function normalizeEnvelope(input:unknown):Envelope {
  const envelope=z.object({commandId:id,issuedAtMs:z.number().int().nonnegative(),kind:z.enum(Object.keys(payloads) as [keyof typeof payloads,...(keyof typeof payloads)[]]),payload:z.record(z.string(),z.unknown())}).strict().safeParse(input);
  if(!envelope.success)throw new DomainError('VALIDATION_FAILED');
  const parsed=payloads[envelope.data.kind].safeParse(envelope.data.payload);
  if(!parsed.success){const errors:Record<string,string>={};for(const issue of parsed.error.issues)errors[issue.path.join('.')||'form']='请检查必填项、长度、结果和日期';throw new DomainError('VALIDATION_FAILED',errors);}
  const payload={...parsed.data} as Record<string,unknown>;
  if(typeof payload.name==='string')payload.name=payload.name.trim();
  if(payload.changes){payload.changes={...(payload.changes as Record<string,unknown>)};const changes=payload.changes as Record<string,unknown>;if(typeof changes.name==='string')changes.name=changes.name.trim();}
  return {...envelope.data,payload};
}
export function canonical(value:unknown):string {if(Array.isArray(value))return `[${value.map(canonical).join(',')}]`;if(value!==null&&typeof value==='object')return `{${Object.keys(value).filter(key=>(value as Record<string,unknown>)[key]!==undefined).sort().map(key=>`${JSON.stringify(key)}:${canonical((value as Record<string,unknown>)[key])}`).join(',')}}`;return JSON.stringify(value);}
export const cloneFacts=(facts:Facts):Facts=>Object.fromEntries(Object.entries(facts).map(([table,rows])=>[table,rows.map((row:object)=>({...row}))])) as unknown as Facts;
function revise(facts:Facts,plans:Set<string>){if(!plans.size)return false;for(const plan of facts.plans)if(plans.has(plan.id))plan.revision++;setMeta(facts,'data_revision',String(Number(metaValue(facts,'data_revision')||0)+1));return true;}
function cancelFuture(facts:Facts,planId:string,now:number,today:string,boundary:number){for(const event of facts.lifecycle_events)if(event.plan_id===planId&&event.cancelled_at_ms===null&&event.effective_at_ms>=boundary)event.cancelled_at_ms=Math.max(now,event.requested_at_ms);for(const rule of facts.rule_versions)if(rule.plan_id===planId&&rule.cancelled_at_ms===null&&rule.effective_on>today)rule.cancelled_at_ms=Math.max(now,rule.created_at_ms);}
function archive(facts:Facts,plan:Plan,event:LifecycleEvent,now:number){cancelFuture(facts,plan.id,now,event.effective_on,event.effective_at_ms);facts.lifecycle_events.push(event);}
export function reconcile(input:Facts,now:number,zone:string,newId:()=>string){
  const facts=cloneFacts(input),today=businessToday(now,zone),touched=new Set<string>();
  for(const plan of facts.plans){
    if(archiveEvent(facts,plan.id,now))continue;
    const candidates:LifecycleEvent[]=[];
    if(plan.type!=='one_time'){
      const end=resolveRule(facts,plan.id,'end_on',today),endOn=end?JSON.parse(end.value_json).endOn as string|null:null;
      if(endOn){const on=addDays(endOn,1,zone),at=dayMs(on,zone);if(at<=now)candidates.push({id:newId(),plan_id:plan.id,kind:'archive',source_key:`cycle_end:${end!.id}`,effective_on:on,effective_at_ms:at,reason:'cycle_end',requested_at_ms:now,cancelled_at_ms:null});}
    }else{
      const result=facts.one_time_results.find(row=>row.plan_id===plan.id);
      if(result&&result.entry_kind==='ordinary'){const on=addDays(result.business_on,1,zone),at=dayMs(on,zone);if(at<=now)candidates.push({id:newId(),plan_id:plan.id,kind:'archive',source_key:`one_time_terminal:${result.id}`,effective_on:on,effective_at_ms:at,reason:'one_time_terminal',requested_at_ms:now,cancelled_at_ms:null});}
    }
    const first=candidates.sort((a,b)=>a.effective_at_ms-b.effective_at_ms)[0];
    if(first&&!facts.lifecycle_events.some(row=>row.plan_id===plan.id&&row.source_key===first.source_key)){archive(facts,plan,first,now);touched.add(plan.id);}
    const appliedKey=`reconciled_at:${plan.id}`,previous=Number(metaValue(facts,appliedKey)||plan.created_at_ms);
    const newlyEffective=events(facts,plan.id).filter(event=>event.kind!=='archive'&&event.effective_at_ms<=now&&event.effective_at_ms>previous);
    if(newlyEffective.length){touched.add(plan.id);setMeta(facts,appliedKey,String(Math.max(...newlyEffective.map(event=>event.effective_at_ms))));}
  }
  const changed=revise(facts,touched);return {facts,changed};
}
function requirePermission(snapshot:Snapshot,plan:Plan,on:string,record?:CycleRecord|Facts['one_time_results'][number]){const right=permission(snapshot,plan,on,record);if(!right.allowed)throw new DomainError(right.reason as DomainError['code']);return right;}
function initialRule(facts:Facts,planId:string,kind:RuleKind,value:unknown,on:string,now:number,newId:()=>string){
  const key={weekday_mask:'weekdayMask',weekly_target:'weeklyTarget',end_on:'endOn',due_on:'dueOn'}[kind];
  const revision=Math.max(0,...facts.rule_versions.filter(row=>row.plan_id===planId&&row.kind===kind).map(row=>row.revision))+1;
  facts.rule_versions.push({id:newId(),plan_id:planId,kind,effective_on:on,revision,value_json:JSON.stringify({[key]:value}),created_at_ms:now,cancelled_at_ms:null});
}
export function applyCommand(input:Facts,envelope:Envelope,now:number,zone:string,newId:()=>string){
  const facts=cloneFacts(input),today=businessToday(now,zone),p=envelope.payload;
  let objectId=p.planId as string,changed=false;
  const snap:Snapshot={facts,asOfMs:now,today,zone,dataRevision:Number(metaValue(facts,'data_revision')||0)};
  if(envelope.kind==='CreatePlan'){
    if(facts.plans.some(plan=>plan.id===p.planId))throw new DomainError('PLAN_CHANGED');
    const type=p.type as Plan['type'],starts=type==='one_time'?today:p.startsOn as string;
    date(starts,zone);if(starts<today)throw new DomainError('VALIDATION_FAILED',{startsOn:'开始日期不能早于今天'});
    if(type==='fixed'&&typeof p.weekdayMask!=='number'||type==='weekly'&&typeof p.weeklyTarget!=='number'||type==='one_time'&&(p.direction!=='do'||!p.dueOn))throw new DomainError('VALIDATION_FAILED');
    if(type!=='fixed'&&p.weekdayMask!==undefined||type!=='weekly'&&p.weeklyTarget!==undefined||type!=='one_time'&&p.dueOn!==undefined||type==='one_time'&&(p.endOn!==undefined||p.startsOn!==undefined))throw new DomainError('VALIDATION_FAILED');
    if(p.endOn){date(p.endOn as string,zone);if((p.endOn as string)<starts)throw new DomainError('VALIDATION_FAILED',{endOn:'结束日期不能早于开始日期'});}
    if(p.dueOn){date(p.dueOn as string,zone);if((p.dueOn as string)<today)throw new DomainError('VALIDATION_FAILED',{dueOn:'截止日期不能早于今天'});}
    const plan:Plan={id:p.planId as string,name:p.name as string,description:p.description as string,type,direction:p.direction as Plan['direction'],created_at_ms:now,created_on:today,starts_on:starts,revision:1};facts.plans.push(plan);
    if(type==='one_time')initialRule(facts,plan.id,'due_on',p.dueOn,today,now,newId);else {initialRule(facts,plan.id,type==='fixed'?'weekday_mask':'weekly_target',type==='fixed'?p.weekdayMask:p.weeklyTarget,today,now,newId);initialRule(facts,plan.id,'end_on',p.endOn??null,today,now,newId);}
    changed=true;
  }else{
    const plan=facts.plans.find(row=>row.id===p.planId);if(!plan)throw new DomainError('TARGET_REMOVED');
    const state=status(facts,plan.id,now);
    if(plan.revision!==p.expectedPlanRevision)throw new DomainError('PLAN_CHANGED');
    switch(envelope.kind){
      case 'SubmitCycleRecord':{
        if(plan.type==='one_time')throw new DomainError('VALIDATION_FAILED');const on=p.businessOn as string;date(on,zone);
        if(p.confirmedToday!==today)throw new DomainError('DAY_CHANGED');const right=requirePermission(snap,plan,on);
        if(right.entryKind!==p.confirmedEntryKind)throw new DomainError('CONFIRMATION_STALE');
        if(facts.cycle_records.some(row=>row.plan_id===plan.id&&row.business_on===on||row.id===p.recordId))throw new DomainError('RECORD_EXISTS');
        facts.cycle_records.push({id:p.recordId as string,plan_id:plan.id,business_on:on,result:p.result as CycleRecord['result'],note:p.note as string,entry_kind:right.entryKind!,submitted_at_ms:now,modified_at_ms:null,revision:1});objectId=p.recordId as string;changed=true;break;
      }
      case 'ModifyCycleRecord':{
        const record=facts.cycle_records.find(row=>row.id===p.recordId&&row.plan_id===plan.id);if(!record)throw new DomainError('TARGET_REMOVED');requirePermission(snap,plan,record.business_on,record);if(record.revision!==p.expectedRecordRevision)throw new DomainError('RECORD_CHANGED');objectId=record.id;
        if(record.result!==p.result||record.note!==p.note){if(!facts.cycle_record_originals.some(row=>row.record_id===record.id))facts.cycle_record_originals.push({record_id:record.id,original_result:record.result,original_note:record.note});record.result=p.result as CycleRecord['result'];record.note=p.note as string;record.modified_at_ms=now;record.revision++;changed=true;}break;
      }
      case 'SubmitOneTimeResult':{
        if(plan.type!=='one_time')throw new DomainError('VALIDATION_FAILED');if(p.confirmedToday!==today)throw new DomainError('DAY_CHANGED');
        if(facts.one_time_results.some(row=>row.plan_id===plan.id||row.id===p.resultId))throw new DomainError('RECORD_EXISTS');
        const completed=p.outcome==='completed',on=completed?p.actualCompletedOn as string:today;
        if(completed&&!on||!completed&&p.actualCompletedOn!==null)throw new DomainError('VALIDATION_FAILED');date(on,zone);const right=requirePermission(snap,plan,on);
        if(right.entryKind!==p.confirmedEntryKind)throw new DomainError('CONFIRMATION_STALE');
        const due=resolveRule(facts,plan.id,'due_on',today)!;
        facts.one_time_results.push({id:p.resultId as string,plan_id:plan.id,business_on:on,outcome:p.outcome as Facts['one_time_results'][number]['outcome'],actual_completed_on:completed?on:null,due_rule_version_id:due.id,note:p.note as string,entry_kind:right.entryKind!,submitted_at_ms:now,modified_at_ms:null,revision:1});objectId=p.resultId as string;
        if(right.entryKind==='backfill')archive(facts,plan,{id:newId(),plan_id:plan.id,kind:'archive',source_key:`historical_terminal:${objectId}`,effective_on:today,effective_at_ms:now,reason:'historical_terminal',requested_at_ms:now,cancelled_at_ms:null},now);changed=true;break;
      }
      case 'ModifyOneTimeResult':{
        const record=facts.one_time_results.find(row=>row.id===p.resultId&&row.plan_id===plan.id);if(!record)throw new DomainError('TARGET_REMOVED');requirePermission(snap,plan,record.business_on,record);if(record.revision!==p.expectedRecordRevision)throw new DomainError('RECORD_CHANGED');objectId=record.id;
        if(record.outcome!==p.outcome||record.note!==p.note){if(!facts.one_time_result_originals.some(row=>row.result_id===record.id))facts.one_time_result_originals.push({result_id:record.id,original_outcome:record.outcome,original_note:record.note});record.outcome=p.outcome as typeof record.outcome;record.actual_completed_on=p.outcome==='completed'?record.business_on:null;record.note=p.note as string;record.modified_at_ms=now;record.revision++;changed=true;}break;
      }
      case 'EditPlan':{
        if(state!=='running')throw new DomainError(state==='paused'?'PAUSED':'ARCHIVED');const changes=p.changes as Record<string,unknown>;
        for(const key of ['name','description'] as const)if(changes[key]!==undefined&&plan[key]!==changes[key]){plan[key]=changes[key] as string;changed=true;}
        for(const [field,kind] of [['weekdayMask','weekday_mask'],['weeklyTarget','weekly_target'],['endOn','end_on'],['dueOn','due_on']] as const){
          if(changes[field]===undefined)continue;if(kind==='weekday_mask'&&plan.type!=='fixed'||kind==='weekly_target'&&plan.type!=='weekly'||kind==='due_on'&&plan.type!=='one_time'||kind==='end_on'&&plan.type==='one_time')throw new DomainError('VALIDATION_FAILED');
          if(kind==='due_on'&&facts.one_time_results.some(row=>row.plan_id===plan.id))throw new DomainError('READ_ONLY');
          if((kind==='end_on'||kind==='due_on')&&changes[field]!==null){date(changes[field] as string,zone);if((changes[field] as string)<today||(kind==='end_on'&&(changes[field] as string)<plan.starts_on))throw new DomainError('VALIDATION_FAILED',{[field]:'请选择今天或未来的有效日期'});}
          const current=ruleValue<unknown>(facts,plan.id,kind,today),pending=facts.rule_versions.filter(row=>row.plan_id===plan.id&&row.kind===kind&&row.cancelled_at_ms===null&&row.effective_on>today);
          if(pending.some(row=>Object.values(JSON.parse(row.value_json))[0]===changes[field])||!pending.length&&current===changes[field])continue;
          const effective=kind==='weekday_mask'?addDays(today,1,zone):kind==='weekly_target'?nextMonday(today,zone):today;
          if((kind==='weekday_mask'||kind==='weekly_target')&&!(p.ruleConfirmations as {field:string;confirmedEffectiveOn:string}[]).some(c=>c.field===kind&&c.confirmedEffectiveOn===effective))throw new DomainError('CONFIRMATION_STALE');
          for(const row of pending)row.cancelled_at_ms=now;
          if(current!==changes[field])initialRule(facts,plan.id,kind,changes[field],effective,now,newId);changed=true;
        }break;
      }
      case 'RequestPause':case 'RequestResume':{
        if(plan.type==='one_time')throw new DomainError('VALIDATION_FAILED');if(state==='archived')throw new DomainError('ARCHIVED');if(pendingState(facts,plan.id,now))throw new DomainError('PLAN_CHANGED');
        if(envelope.kind==='RequestPause'&&state!=='running'||envelope.kind==='RequestResume'&&state!=='paused')throw new DomainError('PLAN_CHANGED');
        const on=addDays(today,1,zone);if(on!==p.confirmedEffectiveOn)throw new DomainError('CONFIRMATION_STALE');
        facts.lifecycle_events.push({id:p.eventId as string,plan_id:plan.id,kind:envelope.kind==='RequestPause'?'pause':'resume',source_key:`user:${p.eventId}`,effective_on:on,effective_at_ms:dayMs(on,zone),reason:'user',requested_at_ms:now,cancelled_at_ms:null});changed=true;break;
      }
      case 'CancelPendingState':{
        if(state==='archived')throw new DomainError('ARCHIVED');const event=facts.lifecycle_events.find(row=>row.id===p.eventId&&row.plan_id===plan.id&&row.cancelled_at_ms===null);if(!event||event.effective_at_ms<=now||event.kind==='archive')throw new DomainError('CONFIRMATION_STALE');event.cancelled_at_ms=now;changed=true;break;
      }
      case 'ArchivePlan':{
        if(state==='archived')throw new DomainError('ARCHIVED');archive(facts,plan,{id:p.eventId as string,plan_id:plan.id,kind:'archive',source_key:`user:${p.eventId}`,effective_on:today,effective_at_ms:now,reason:'user',requested_at_ms:now,cancelled_at_ms:null},now);changed=true;break;
      }
      case 'PermanentlyDeletePlan':{
        if(state!=='archived')throw new DomainError('READ_ONLY');const cycleIds=new Set(facts.cycle_records.filter(row=>row.plan_id===plan.id).map(row=>row.id)),onceIds=new Set(facts.one_time_results.filter(row=>row.plan_id===plan.id).map(row=>row.id));
        facts.plans=facts.plans.filter(row=>row.id!==plan.id);facts.rule_versions=facts.rule_versions.filter(row=>row.plan_id!==plan.id);facts.lifecycle_events=facts.lifecycle_events.filter(row=>row.plan_id!==plan.id);facts.cycle_records=facts.cycle_records.filter(row=>row.plan_id!==plan.id);facts.one_time_results=facts.one_time_results.filter(row=>row.plan_id!==plan.id);facts.cycle_record_originals=facts.cycle_record_originals.filter(row=>!cycleIds.has(row.record_id));facts.one_time_result_originals=facts.one_time_result_originals.filter(row=>!onceIds.has(row.result_id));
        facts.app_meta=facts.app_meta.filter(row=>row.key!==`reconciled_at:${plan.id}`);
        for(const receipt of facts.command_receipts)if(receipt.plan_id===plan.id){receipt.plan_id=null;receipt.object_id=null;receipt.payload_digest=null;receipt.result_code='TARGET_REMOVED';}changed=true;break;
      }
    }
    if(changed&&envelope.kind!=='PermanentlyDeletePlan')plan.revision++;
  }
  if(changed)setMeta(facts,'data_revision',String(Number(metaValue(facts,'data_revision')||0)+1));
  return {facts,changed,objectId};
}
export function receiptResult(receipt:Receipt|undefined,envelope:Envelope,digest:string,now:number){
  if(receipt?.result_code==='TARGET_REMOVED')throw new DomainError('TARGET_REMOVED');
  if(envelope.issuedAtMs>now)throw new DomainError('CLOCK_CHANGED');if(now>=envelope.issuedAtMs+604800000)throw new DomainError('COMMAND_EXPIRED');
  if(receipt){if(receipt.payload_digest!==digest)throw new DomainError('COMMAND_ID_REUSED');return receipt.object_id||undefined;}
  return null;
}
