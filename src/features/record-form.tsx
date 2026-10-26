import { useRef, useState } from 'react';
import {View} from 'react-native';
import { router } from 'expo-router';
import * as Crypto from 'expo-crypto';
import { Envelope } from '../domain/model';
import { permission, resolveRule, ruleValue } from '../domain/rules';
import { date, formatInstant } from '../domain/date';
import { errorMessage, useApp } from '../state/AppProvider';
import { Body, Button, Choice, DateField, Field, Metal, Notice, Page, confirm } from '../ui/metal';
import { useDraftGuard } from './draft';
import { resultColor, resultText, resultLabel } from './shared';
import {RecordFormView} from '../ui/screens/RecordFormView';
import {RecordFeedbackView} from '../ui/screens/RecordFeedbackView';
import {recordPresentation} from '../ui/record-presentation';
import {walk,literal} from '../ui/screens/TodayView';
import {SpecFragment} from '../ui/spec-renderer';
import type {NodeAction,SpecNode} from '../ui/spec-types';

export default function RecordForm({planId,businessOn,recordId,preset}:{planId:string;businessOn?:string;recordId?:string;preset?:string}){
  const app=useApp(),{snapshot}=app,plan=snapshot.facts.plans.find(row=>row.id===planId),record=snapshot.facts.cycle_records.find(row=>row.id===recordId&&row.plan_id===planId)||snapshot.facts.one_time_results.find(row=>row.id===recordId&&row.plan_id===planId);
  const [result,setResult]=useState(record?('result'in record?record.result:record.outcome):preset||''),[note,setNote]=useState(record?.note||''),[on,setOn]=useState(record?.business_on||businessOn||snapshot.today),[dirty,setDirty]=useState(!record&&!!preset),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[fields,setFields]=useState<Record<string,string>>({});
  const frozen=useRef<Envelope|null>(null),confirmedToday=useRef(snapshot.today),revisions=useRef({plan:plan?.revision,record:record?.revision}),objectId=useRef(Crypto.randomUUID());
  const allowLeave=useDraftGuard(dirty,busy);
  const right=plan?permission(snapshot,plan,on,record):{allowed:false,reason:'TARGET_REMOVED'};
  const modify=record&&right.allowed;
  const change=(callback:()=>void)=>{if(busy)return;callback();setDirty(true);frozen.current=null;setError(null);setFields({});};
  async function save(){if(!plan||busy)return;setFields({});if(!result){setError('VALIDATION_FAILED');return;}
    if(!frozen.current){
      if(!record&&confirmedToday.current===snapshot.today&&on<snapshot.today&&(plan.type!=='one_time'||result==='completed')&&!await confirm(plan.type==='one_time'?'确认历史完成补报':'确认补记',plan.type==='one_time'?`${on} 的完成结果保存后将立即归档，永久只读。`:`${on} 的补记保存后立即只读，不能修改或撤回。`))return;
      if(!record&&confirmedToday.current===snapshot.today&&plan.direction==='avoid'&&result==='success'&&!await confirm('确认截至当前的情况','你主动确认截至目前没有发生目标行为；当天如果发生，仍需修改为失败。'))return;
      const common={planId:plan.id,expectedPlanRevision:revisions.current.plan,note};
      const first={confirmedToday:confirmedToday.current,confirmedEntryKind:on===confirmedToday.current?'ordinary':'backfill'};
      frozen.current=app.envelope(plan.type==='one_time'?(record?'ModifyOneTimeResult':'SubmitOneTimeResult'):(record?'ModifyCycleRecord':'SubmitCycleRecord'),plan.type==='one_time'?{...common,resultId:record?.id||objectId.current,outcome:result,...(record?{expectedRecordRevision:revisions.current.record}:{...first,actualCompletedOn:result==='completed'?on:null})}:{...common,recordId:record?.id||objectId.current,result,...(record?{expectedRecordRevision:revisions.current.record}:{...first,businessOn:on})});
    }
    setBusy(true);const saved=await app.execute(frozen.current);setBusy(false);
    if(saved.ok){setDirty(false);allowLeave();router.back();}else{setError(saved.code);setFields(saved.fieldErrors||{});if(!saved.code.startsWith('STORAGE_'))frozen.current=null;}
  }
  if(!plan||recordId&&!record)return <Page title="查看记录" back><Notice error>目标已永久删除或记录不可用。</Notice></Page>;
  const values=plan.type==='one_time'?['completed','failed','cancelled']:['success','failure','skip'];
  const original=record?('result'in record?snapshot.facts.cycle_record_originals.find(row=>row.record_id===record.id):snapshot.facts.one_time_result_originals.find(row=>row.result_id===record.id)):undefined;
  const referencedDue=record&&'due_rule_version_id'in record?snapshot.facts.rule_versions.find(row=>row.id===record.due_rule_version_id):resolveRule(snapshot.facts,plan.id,'due_on',snapshot.today);
  const reconfirmOn=plan.type==='one_time'&&result!=='completed'?snapshot.today:on;
  let completionPreview:string|undefined;
  if(plan.type==='one_time'&&result==='completed'&&!record&&referencedDue){
    try{date(on,snapshot.zone);if(on>=plan.created_on&&on<=snapshot.today)completionPreview=on<=JSON.parse(referencedDue.value_json).dueOn?'按时完成':'迟完成';}catch{}
  }
  const {document,inputs}=recordPresentation({name:plan.name,direction:plan.direction,type:plan.type,note,on,today:snapshot.today,zone:snapshot.zone,due:referencedDue?String(JSON.parse(referencedDue.value_json).dueOn):snapshot.today,submittedAt:new Date(record?.submitted_at_ms??snapshot.asOfMs).toISOString(),originalNote:original?.original_note??record?.note??'',originalSubmittedAt:new Date(record?.submitted_at_ms??snapshot.asOfMs).toISOString(),readonly:!right.allowed,modify:!!modify,error,scheduleLabel:plan.type==='weekly'?'每周 '+ruleValue<number>(snapshot.facts,plan.id,'weekly_target',on)+' 天':'固定日期'}),nodes=walk(document.tree),actions:Record<string,NodeAction>={},overrides:Record<string,SpecNode>={};
  const find=(label:string)=>nodes.find(n=>n.name===label),bind=(label:string,action:NodeAction)=>{const n=find(label);if(n)actions[n.id]=action;};
  bind('标题触控区域',{label:'返回',onPress:()=>router.back()});bind('返回日历',{onPress:()=>router.back()});bind('返回继续编辑',{onPress:()=>setError(null)});bind('重试保存',{testID:'record.save',disabled:busy,onPress:()=>void save()});
  const changeResult=(value:string)=>change(()=>{setResult(value);if(plan.type==='one_time'&&!record&&value!=='completed')setOn(snapshot.today);});
  for(const [value,labels] of [['success',['✓ 成功选项','✓ 做到了选项']],['failure',['× 失败选项','× 发生了选项']],['skip',['— 跳过选项']]] as const){for(const label of labels){const n=find(label);if(!n)continue;actions[n.id]={testID:'record.result.'+value,selected:result===value,disabled:busy||!right.allowed,onPress:()=>changeResult(value)};overrides[n.id]={...n,styleRef:result===value?(value==='success'?'s-0e36cd6a3eb24da9':value==='failure'?'s-31fec9739b4ffa8d':'s-3d9eec7358fb85e8'):'s-17918eeb59c2274a'};}}
  for(const label of ['文字备注（可选）内容','文字备注内容'])bind(label,{testID:'record.note',input:{value:note,onChange:v=>change(()=>setNote(v)),multiline:true,editable:right.allowed&&!busy,label:'文字备注（可选）'}});
  const readonlyResult=find('历史结果');if(readonlyResult&&record){for(const n of walk(readonlyResult).filter(n=>n.content?.type==='text'&&!n.content.binding)){if(n.content!.value?.includes('成功'))overrides[n.id]=literal(n,resultText(plan,result as Parameters<typeof resultText>[1]));}}
  for(const n of nodes.filter(n=>['保存记录','保存修改','保存补记','保存完成记录'].includes(n.name))){actions[n.id]={testID:'record.save',disabled:busy||!result,onPress:()=>void save()};if(busy)for(const child of n.children.filter(c=>c.kind==='text'))overrides[child.id]=literal(child,'正在保存…');}
  bind('进入补记确认',{testID:'record.reconfirm',onPress:async()=>{if(await confirm('日期已变化','现在是 '+snapshot.today+'。保留原输入，重新确认 '+reconfirmOn+' '+(reconfirmOn<snapshot.today?'作为补记，保存后永久只读':'作为普通记录')+'。')){setOn(reconfirmOn);confirmedToday.current=snapshot.today;revisions.current={plan:plan.revision,record:undefined};frozen.current=null;setError(null);}}});
  const slots:Record<string,React.ReactNode>={};const dateNode=find('实际完成日期输入');if(dateNode)slots[dateNode.id]=<DateField label="实际完成日期" value={on} min={plan.created_on} max={snapshot.today} zone={snapshot.zone} testID="record.actualCompletedOn" disabled={busy} error={fields.actualCompletedOn||fields.date||(error==='DATE_INELIGIBLE'?'实际完成日期必须在创建日到今天之间。':undefined)} onChange={v=>change(()=>setOn(v!))}/>;
  const saveNode=nodes.find(n=>['保存记录','保存修改','保存补记','保存完成记录'].includes(n.name));if(saveNode){slots[saveNode.id]=<View style={{gap:12}}>{completionPreview&&<Body strong>{completionPreview}</Body>}{Object.entries(fields).map(([key,message])=><Notice key={key} error>{message}</Notice>)}{error&&!error.startsWith('STORAGE_')&&error!=='DAY_CHANGED'&&<Notice error>{errorMessage(error)}</Notice>}{error&&['PLAN_CHANGED','RECORD_CHANGED','CONFIRMATION_STALE'].includes(error)&&right.allowed&&<Button title="使用最新状态重新确认" onPress={async()=>{if(await confirm('重新确认最新状态','保留你的输入，按最新计划和记录版本提交？')){revisions.current={plan:plan.revision,record:record?.revision};confirmedToday.current=snapshot.today;frozen.current=null;setError(null);}}}/>}{plan.type==='one_time'&&<Choice disabled={busy||!right.allowed} value={result} onChange={changeResult} options={values.map(value=>({value,label:resultLabel(plan,value as Parameters<typeof resultText>[1]),color:resultColor(value)}))} testID="record.result"/>}<SpecFragment node={saveNode} inputs={inputs} actions={actions} overrides={overrides}/></View>;}
  return error==='DAY_CHANGED'||error?.startsWith('STORAGE_')?<RecordFeedbackView dateChanged={error==='DAY_CHANGED'} inputs={inputs} actions={actions} overrides={overrides} slots={slots}/>:<RecordFormView document={document} inputs={inputs} actions={actions} overrides={overrides} slots={slots}/>;
}
