import { useRef, useState } from 'react';
import { View } from 'react-native';
import { router } from 'expo-router';
import * as Crypto from 'expo-crypto';
import { Direction, Envelope, PlanType } from '../domain/model';
import { addDays, nextMonday } from '../domain/date';
import { pendingRules, ruleValue, status } from '../domain/rules';
import { errorMessage, useApp } from '../state/AppProvider';
import { Body, Button, Choice, DateField, Field, Notice, Page, confirm } from '../ui/metal';
import { useDraftGuard } from './draft';

export default function PlanForm({planId}:{planId?:string}){
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
  return <Page title={plan?'编辑计划':'新建计划'} back><Field editable={!busy} label="名称" value={name} onChangeText={value=>change(setName,value)} testID="plan.name" error={fields.name||fields['changes.name']}/><Body>{[...name.trim()].length}/80 字</Body>{!plan&&<><Choice disabled={busy} value={type} onChange={value=>void changeType(value as PlanType)} options={[{value:'fixed',label:'固定星期'},{value:'weekly',label:'每周目标'},{value:'one_time',label:'一次性'}]} testID="plan.type"/>{type!=='one_time'&&<Choice disabled={busy} value={direction} onChange={value=>change(setDirection,value as Direction)} options={[{value:'do',label:'要做'},{value:'avoid',label:'不要做'}]} testID="plan.direction"/>}</>}{plan&&<Body>类型、方向、开始日期与固定时区不能修改。</Body>}{type==='fixed'&&<><Body title>执行星期</Body><View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>{['一','二','三','四','五','六','日'].map((label,index)=><View key={label} style={{flexBasis:48,flexGrow:1}}><Button title={`周${label}`} selected={!!(mask&(1<<index))} disabled={busy} testID={`plan.weekday.${index+1}`} onPress={()=>change(setMask,mask^(1<<index))}/></View>)}</View><Button title="每日（全选）" disabled={busy} testID="plan.weekday.everyday" onPress={()=>change(setMask,127)}/><Body>{mask===127?'每日':mask?['一','二','三','四','五','六','日'].filter((_,i)=>!!(mask&(1<<i))).map(day=>`周${day}`).join('、'):'默认不选，请至少选择一个星期。'}</Body></>}{type==='weekly'&&<Field editable={!busy} label="每周目标天数（1–7）" value={target} keyboardType="number-pad" onChangeText={value=>change(setTarget,value)} testID="plan.weeklyTarget" error={fields.weeklyTarget||fields['changes.weeklyTarget']}/>}{type!=='one_time'?<>{!plan&&<DateField disabled={busy} label="开始日期" value={starts} min={snapshot.today} zone={snapshot.zone} testID="plan.startsOn" error={fields.startsOn} onChange={value=>change(setStarts,value!)}/>}<DateField disabled={busy} label="结束日期（可不设置）" value={end} min={starts>snapshot.today?starts:snapshot.today} nullable zone={snapshot.zone} testID="plan.endOn" error={fields.endOn||fields['changes.endOn']} onChange={value=>change(setEnd,value)}/></>:<DateField disabled={busy||dueLocked} label="截止日期" value={due} min={snapshot.today} zone={snapshot.zone} testID="plan.dueOn" error={fields.dueOn||fields['changes.dueOn']} onChange={value=>change(setDue,value!)}/>}{dueLocked&&<Body>已有结果，截止日期已锁定；未归档当天仍可修改名称和说明。</Body>}<Field editable={!busy} label="说明（可选）" value={description} multiline onChangeText={value=>change(setDescription,value)} testID="plan.description" error={fields.description||fields['changes.description']}/><Body>计划时区：{snapshot.zone} · 首次使用后固定</Body>{error&&<Notice error>{errorMessage(error)}</Notice>}{error&&['PLAN_CHANGED','CONFIRMATION_STALE'].includes(error)&&<Button title="加载最新状态后重新确认" onPress={async()=>{const latest=await app.refresh();if(!latest)return;planRevision.current=latest.facts.plans.find(row=>row.id===planId)?.revision;frozen.current=null;setError(null);}}/>}<Button title={busy?'正在保存…':'保存计划'} disabled={busy||(type==='fixed'&&mask===0)} testID="plan.save" onPress={()=>void save()}/></Page>;
}
