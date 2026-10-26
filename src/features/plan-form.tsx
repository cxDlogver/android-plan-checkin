import { useRef, useState } from 'react';
import { View, Modal } from 'react-native';
import { router } from 'expo-router';
import * as Crypto from 'expo-crypto';
import { Direction, Envelope, PlanType } from '../domain/model';
import { addDays, nextMonday } from '../domain/date';
import { pendingRules, ruleValue, status } from '../domain/rules';
import { errorMessage, useApp } from '../state/AppProvider';
import { Body, Button, Choice, DateField, Field, Notice, Page, MetaLine, confirm } from '../ui/metal';
import { useDraftGuard } from './draft';
import {PlanFormView} from '../ui/screens/PlanFormView';
import {byName,walk,literal,actionsByName} from '../ui/screens/TodayView';
import {planFormPresentation} from '../ui/plan-form-presentation';
import {SpecFragment} from '../ui/spec-renderer';
import type {NodeAction,SpecNode} from '../ui/spec-types';

export default function PlanForm({planId}:{planId?:string}){
  const [dateDialog,setDateDialog]=useState(false);
  const app=useApp(),{snapshot}=app,plan=snapshot.facts.plans.find(row=>row.id===planId),pending=plan?pendingRules(snapshot.facts,plan.id,snapshot.today):[];
  const initial=(kind:'weekday_mask'|'weekly_target'|'end_on'|'due_on')=>pending.find(row=>row.kind===kind)?Object.values(JSON.parse(pending.find(row=>row.kind===kind)!.value_json))[0]:plan?ruleValue(snapshot.facts,plan.id,kind,snapshot.today):undefined;
  const [name,setName]=useState(plan?.name||''),[description,setDescription]=useState(plan?.description||''),[type,setType]=useState<PlanType>(plan?.type||'fixed'),[direction,setDirection]=useState<Direction>(plan?.direction||'do'),[mask,setMask]=useState<number>(initial('weekday_mask') as number||0),[target,setTarget]=useState(String(initial('weekly_target')||3)),[starts,setStarts]=useState(plan?.starts_on||snapshot.today),[end,setEnd]=useState<string|null>(initial('end_on') as string|null||null),[due,setDue]=useState(initial('due_on') as string||snapshot.today),[dirty,setDirty]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[fields,setFields]=useState<Record<string,string>>({});
  const frozen=useRef<Envelope|null>(null),planRevision=useRef(plan?.revision),objectId=useRef(Crypto.randomUUID()),initialValues=useRef({name:plan?.name||'',description:plan?.description||'',mask:initial('weekday_mask'),target:initial('weekly_target'),end:initial('end_on')??null,due:initial('due_on')});
  const allowLeave=useDraftGuard(dirty,busy);
  const change=<T,>(setter:(value:T)=>void,value:T)=>{if(busy)return;setter(value);setDirty(true);frozen.current=null;setError(null);};
  async function changeType(value:PlanType){
    if(value===type)return;
    if(!await confirm('切换计划类型','切换后将清除不适用的星期、目标和日期输入；名称与说明会保留。'))return;
    setMask(0);setTarget('3');setStarts(snapshot.today);setEnd(null);setDue(snapshot.today);
    if(value==='one_time')setDirection('do');
    change(setType,value);
  }
  async function save(){
    if(busy)return;setFields({});
    const expected:Record<string,unknown>={};
    if(plan){
      if(name.trim()!==initialValues.current.name)expected.name=name;
      if(description!==initialValues.current.description)expected.description=description;
      if(type==='fixed'&&mask!==initialValues.current.mask)expected.weekdayMask=mask;
      if(type==='weekly'&&Number(target)!==initialValues.current.target)expected.weeklyTarget=Number(target);
      if(type!=='one_time'&&end!==initialValues.current.end)expected.endOn=end;
      if(type==='one_time'&&due!==initialValues.current.due)expected.dueOn=due;
      const rules: {field:'weekday_mask'|'weekly_target';confirmedEffectiveOn:string}[]=[];
      if(expected.weekdayMask!==undefined)rules.push({field:'weekday_mask',confirmedEffectiveOn:addDays(snapshot.today,1,snapshot.zone)});
      if(expected.weeklyTarget!==undefined)rules.push({field:'weekly_target',confirmedEffectiveOn:nextMonday(snapshot.today,snapshot.zone)});
      if(!frozen.current){if(rules.length&&!await confirm('确认规则变更',rules.map(rule=>`${rule.field==='weekday_mask'?'星期选择':'每周目标'}将于 ${rule.confirmedEffectiveOn} 生效；历史不会重算规则。`).join('\n')))return;frozen.current=app.envelope('EditPlan',{planId:plan.id,expectedPlanRevision:planRevision.current,changes:expected,ruleConfirmations:rules});}
    }else if(!frozen.current){frozen.current=app.envelope('CreatePlan',{planId:objectId.current,name,description,type,direction:type==='one_time'?'do':direction,...(type==='one_time'?{dueOn:due}:{startsOn:starts,endOn:end,...(type==='fixed'?{weekdayMask:mask}:{weeklyTarget:Number(target)})})});}
    setBusy(true);const result=await app.execute(frozen.current!);setBusy(false);
    if(result.ok){setDirty(false);allowLeave();if(plan)router.back();else router.replace({pathname:'/plans/[planId]',params:{planId:objectId.current}});}
    else {setError(result.code);setFields(result.fieldErrors||{});if(!result.code.startsWith('STORAGE_'))frozen.current=null;}
  }
  const dueLocked=!!plan&&type==='one_time'&&snapshot.facts.one_time_results.some(row=>row.plan_id===plan.id);
  if(planId&&!plan)return <Page title="编辑计划" back><Notice error>目标已永久删除。</Notice></Page>;
  if(plan&&status(snapshot.facts,plan.id,snapshot.asOfMs)!=='running')return <Page title="编辑计划" back><Notice>计划已暂停或归档，不能编辑基本信息。</Notice></Page>;
  const {document,inputs}=planFormPresentation({editing:!!plan,type,name,description,zone:snapshot.zone,target,due}),nodes=walk(document.tree),actions:Record<string,NodeAction>={},overrides:Record<string,SpecNode>={};
  const find=(label:string)=>nodes.find(n=>n.name===label),bind=(label:string,action:NodeAction)=>{const n=find(label);if(n)actions[n.id]=action;};
  bind('标题触控区域',{label:'返回',onPress:()=>router.back()});
  bind('名称内容',{testID:'plan.name',input:{value:name,onChange:v=>change(setName,v),editable:!busy,label:'名称'}});
  bind(plan?'说明内容':'说明（可选）内容',{testID:'plan.description',input:{value:description,onChange:v=>change(setDescription,v),multiline:true,editable:!busy,label:'说明（可选）'}});
  const choose=(label:string,selected:boolean,testID:string,onPress:()=>void)=>{const n=find(label);if(!n)return;actions[n.id]={testID,selected,disabled:busy,onPress};overrides[n.id]={...n,styleRef:selected?'s-3d9eec7358fb85e8':'s-17918eeb59c2274a'};const child=n.children.find(c=>c.kind==='text');if(child){const normal=nodes.find(c=>c.name==='不要做'||c.name==='固定日期'),selectedText=nodes.find(c=>c.name==='要做'||c.name==='一次性');if((selected?selectedText:normal)?.styleRef)overrides[child.id]={...child,styleRef:(selected?selectedText:normal)!.styleRef};}};
  if(!plan){for(const [value,label] of [['fixed','固定日期选项'],['weekly','每周目标选项'],['one_time','一次性选项']] as const)choose(label,type===value,'plan.type.'+value,()=>void changeType(value));for(const [value,label] of [['do','要做选项'],['avoid','不要做选项']] as const)choose(label,direction===value,'plan.direction.'+value,()=>change(setDirection,value));}
  if(type==='fixed'){
   for(const [i,day] of ['一','二','三','四','五','六','日'].entries())choose('星期'+day,!!(mask&(1<<i)),'plan.weekday.'+(i+1),()=>change(setMask,mask^(1<<i)));
   const descriptionNode=find('每日说明');if(descriptionNode)overrides[descriptionNode.id]=literal(descriptionNode,mask===127?'已选择每天':mask?'已选择 '+['一','二','三','四','五','六','日'].filter((_,i)=>mask&(1<<i)).map(d=>'周'+d).join('、'):'请至少选择一个星期');
   choose('每天选项',mask===127,'plan.weekday.everyday',()=>change(setMask,127));choose('指定星期选项',mask!==127,'plan.weekday.custom',()=>{if(mask===127)change(setMask,0);});
  }
  bind('−选项',{testID:'plan.weeklyTarget.minus',disabled:busy||Number(target)<=1,onPress:()=>change(setTarget,String(Math.max(1,Number(target)-1)))});bind('＋选项',{testID:'plan.weeklyTarget.plus',disabled:busy||Number(target)>=7,onPress:()=>change(setTarget,String(Math.min(7,Number(target)+1)))});bind('3 天',{testID:'plan.weeklyTarget',input:{value:target,onChange:v=>change(setTarget,v),editable:!busy,label:'每周目标天数'}});
  for(const label of ['开始 / 结束输入','结束日期输入','截止日期输入'])bind(label,{testID:label==='截止日期输入'?'plan.dueOn':label==='结束日期输入'?'plan.endOn':'plan.dates',disabled:busy||dueLocked,onPress:()=>setDateDialog(true)});
  const dates=find('开始 / 结束内容');if(dates)overrides[dates.id]=literal(dates,starts+' 开始 · '+(end||'不设置结束'));const endText=find('结束日期内容');if(endText)overrides[endText.id]=literal(endText,end||'不设置结束日期');
  const saveNode=nodes.find(n=>['保存计划','保存任务','保存修改'].includes(n.name))!;actions[saveNode.id]={testID:'plan.save',disabled:busy||(type==='fixed'&&mask===0),onPress:()=>void save()};if(busy)for(const child of saveNode.children.filter(c=>c.kind==='text'))overrides[child.id]=literal(child,'正在保存…');
  const extras=<View style={{gap:12}}>{Object.entries(fields).map(([key,message])=><Notice key={key} error>{message}</Notice>)}{error&&<Notice error>{errorMessage(error)}</Notice>}{error&&['PLAN_CHANGED','CONFIRMATION_STALE'].includes(error)&&<Button title="加载最新状态后重新确认" onPress={async()=>{const latest=await app.refresh();if(!latest)return;planRevision.current=latest.facts.plans.find(row=>row.id===planId)?.revision;frozen.current=null;setError(null);}}/>}{type==='fixed'&&<Button title="每日（全选）" disabled={busy} testID="plan.weekday.everyday" onPress={()=>change(setMask,127)}/>}{plan&&type==='fixed'&&<Choice disabled={busy} value={String(mask)} onChange={value=>change(setMask,Number(value))} options={['一','二','三','四','五','六','日'].map((d,i)=>({value:String(mask^(1<<i)),label:'星期'+d}))}/>}{plan&&type==='weekly'&&<Field label="每周目标天数（1–7）" editable={!busy} value={target} onChangeText={v=>change(setTarget,v)} testID="plan.weeklyTarget"/>}{plan&&type==='one_time'&&<DateField disabled={busy||dueLocked} label="截止日期" value={due} min={snapshot.today} zone={snapshot.zone} onChange={v=>change(setDue,v!)} testID="plan.dueOn"/>}<SpecFragment node={saveNode} inputs={inputs} actions={actions} overrides={overrides}/></View>;
  return <><PlanFormView document={document} inputs={inputs} actions={actions} overrides={overrides} slots={{[saveNode.id]:extras}}/><Modal visible={dateDialog} transparent animationType="fade" onRequestClose={()=>setDateDialog(false)}><View style={{flex:1,justifyContent:'center',padding:16,backgroundColor:'#0008'}}><View style={{backgroundColor:'#E8ECF0',padding:16,gap:16}}>{type==='one_time'?<DateField disabled={busy||dueLocked} label="截止日期" value={due} min={snapshot.today} zone={snapshot.zone} testID="plan.dueOn" onChange={v=>change(setDue,v!)}/>:<>{!plan&&<DateField disabled={busy} label="开始日期" value={starts} min={snapshot.today} zone={snapshot.zone} testID="plan.startsOn" onChange={v=>change(setStarts,v!)}/>}<DateField disabled={busy} nullable label="结束日期（可不设置）" value={end} min={starts>snapshot.today?starts:snapshot.today} zone={snapshot.zone} testID="plan.endOn" onChange={v=>change(setEnd,v)}/></>}<Button title="完成日期设置" onPress={()=>setDateDialog(false)}/></View></View></Modal></>;
}
