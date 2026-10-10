import { useRef, useState } from 'react';
import { router } from 'expo-router';
import * as Crypto from 'expo-crypto';
import { Envelope } from '../domain/model';
import { permission, resolveRule, ruleValue } from '../domain/rules';
import { formatInstant } from '../domain/date';
import { errorMessage, useApp } from '../state/AppProvider';
import { Body, Button, Choice, DateField, Field, Metal, Notice, Page, confirm } from '../ui/metal';
import { useDraftGuard } from './draft';
import { resultColor, resultText } from './shared';

export default function RecordForm({planId,businessOn,recordId,preset}:{planId:string;businessOn?:string;recordId?:string;preset?:string}){
  const app=useApp(),{snapshot}=app,plan=snapshot.facts.plans.find(row=>row.id===planId),record=snapshot.facts.cycle_records.find(row=>row.id===recordId&&row.plan_id===planId)||snapshot.facts.one_time_results.find(row=>row.id===recordId&&row.plan_id===planId);
  const [result,setResult]=useState(record?('result'in record?record.result:record.outcome):preset||''),[note,setNote]=useState(record?.note||''),[on,setOn]=useState(record?.business_on||businessOn||snapshot.today),[dirty,setDirty]=useState(!record&&!!preset),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null);
  const frozen=useRef<Envelope|null>(null),confirmedToday=useRef(snapshot.today),revisions=useRef({plan:plan?.revision,record:record?.revision}),objectId=useRef(Crypto.randomUUID());
  const allowLeave=useDraftGuard(dirty,busy);
  const right=plan?permission(snapshot,plan,on,record):{allowed:false,reason:'TARGET_REMOVED'};
  const modify=record&&right.allowed;
  const change=(callback:()=>void)=>{callback();setDirty(true);frozen.current=null;setError(null);};
  async function save(){if(!plan||busy)return;if(!result){setError('VALIDATION_FAILED');return;}
    if(!frozen.current){
      if(!record&&on<snapshot.today&&!await confirm(plan.type==='one_time'?'确认历史完成补报':'确认补记',plan.type==='one_time'?`${on} 的完成结果保存后将立即归档，永久只读。`:`${on} 的补记保存后立即只读，不能修改或撤回。`))return;
      if(!record&&plan.direction==='avoid'&&result==='success'&&!await confirm('确认截至当前的情况','你主动确认截至目前没有发生目标行为；当天如果发生，仍需修改为失败。'))return;
      const common={planId:plan.id,expectedPlanRevision:revisions.current.plan,note};
      const first={confirmedToday:confirmedToday.current,confirmedEntryKind:on===confirmedToday.current?'ordinary':'backfill'};
      frozen.current=app.envelope(plan.type==='one_time'?(record?'ModifyOneTimeResult':'SubmitOneTimeResult'):(record?'ModifyCycleRecord':'SubmitCycleRecord'),plan.type==='one_time'?{...common,resultId:record?.id||objectId.current,outcome:result,...(record?{expectedRecordRevision:revisions.current.record}:{...first,actualCompletedOn:result==='completed'?on:null})}:{...common,recordId:record?.id||objectId.current,result,...(record?{expectedRecordRevision:revisions.current.record}:{...first,businessOn:on})});
    }
    setBusy(true);const saved=await app.execute(frozen.current);setBusy(false);
    if(saved.ok){setDirty(false);allowLeave();router.back();}else{setError(saved.code);if(!saved.code.startsWith('STORAGE_'))frozen.current=null;}
  }
  if(!plan||recordId&&!record)return <Page title="查看记录" back><Notice error>目标已永久删除或记录不可用。</Notice></Page>;
  const values=plan.type==='one_time'?['completed','failed','cancelled']:['success','failure','skip'];
  const original=record?('result'in record?snapshot.facts.cycle_record_originals.find(row=>row.record_id===record.id):snapshot.facts.one_time_result_originals.find(row=>row.result_id===record.id)):undefined;
  const referencedDue=record&&'due_rule_version_id'in record?snapshot.facts.rule_versions.find(row=>row.id===record.due_rule_version_id):resolveRule(snapshot.facts,plan.id,'due_on',snapshot.today);
  return <Page title={record?(modify?'查看或修改记录':'只读记录'):on<snapshot.today?'历史补记':'确认记录'} back><Metal><Body title>{plan.name}</Body><Body>{on} · {plan.direction==='avoid'?'不要做':'要做'}</Body>{plan.type==='one_time'&&<Body>截止：{referencedDue?JSON.parse(referencedDue.value_json).dueOn:ruleValue(snapshot.facts,plan.id,'due_on',snapshot.today)}</Body>}</Metal>{!right.allowed&&<Notice>{errorMessage(right.reason||'READ_ONLY')}</Notice>}{right.allowed?<Choice value={result} onChange={value=>change(()=>{setResult(value);if(plan.type==='one_time'&&!record&&value!=='completed')setOn(snapshot.today);})} options={values.map(value=>({value,label:resultText(plan,value as Parameters<typeof resultText>[1]),color:resultColor(value)}))} testID="record.result"/>:<Body title style={{color:resultColor(result)}}>{resultText(plan,result as Parameters<typeof resultText>[1])}</Body>}{plan.type==='one_time'&&result==='completed'&&!record&&<DateField label="实际完成日期" value={on} min={plan.created_on} max={snapshot.today} zone={snapshot.zone} testID="record.actualCompletedOn" onChange={value=>change(()=>setOn(value!))}/>}<Field label="文字备注（可选）" value={note} multiline editable={right.allowed} onChangeText={value=>change(()=>setNote(value))} testID="record.note"/><Body>{[...note].length}/2000 字</Body>{record&&<Metal><Body>首次提交：{formatInstant(record.submitted_at_ms,snapshot.zone)}</Body>{record.modified_at_ms!==null&&<Body>最近修改：{formatInstant(record.modified_at_ms,snapshot.zone)} · 已修正</Body>}<Body>{record.entry_kind==='backfill'?'历史补记 · 永久只读':'普通记录 · 仅业务日当天可修改'}</Body>{original&&<><Body strong>首次修正前的原值</Body><Body>{'original_result'in original?resultText(plan,original.original_result):resultText(plan,original.original_outcome)}</Body><Body>{original.original_note||'无备注'}</Body></>}</Metal>}{!record&&on<snapshot.today&&<Notice>补记保存后立即只读；一次性历史完成补报将立即归档。</Notice>}{error&&<Notice error>{errorMessage(error)}</Notice>}{error==='DAY_CHANGED'&&!record&&right.allowed&&<Button title={on<snapshot.today?'进入补记确认':'重新确认当前业务日'} testID="record.reconfirm" onPress={async()=>{if(await confirm('日期已变化',`现在是 ${snapshot.today}。保留原输入，重新确认 ${on} ${on<snapshot.today?'作为补记，保存后永久只读':'作为普通记录'}。`)){confirmedToday.current=snapshot.today;revisions.current={plan:plan.revision,record:undefined};frozen.current=null;setError(null);}}}/>}{error&&['PLAN_CHANGED','RECORD_CHANGED','CONFIRMATION_STALE'].includes(error)&&right.allowed&&<Button title="使用最新状态重新确认" onPress={async()=>{if(await confirm('重新确认最新状态','保留你的输入，按最新计划和记录版本提交？')){revisions.current={plan:plan.revision,record:record?.revision};confirmedToday.current=snapshot.today;frozen.current=null;setError(null);}}}/>}{right.allowed&&<Button title={busy?'正在保存…':'确认保存'} disabled={busy} testID="record.save" onPress={()=>void save()}/>}</Page>;
}
