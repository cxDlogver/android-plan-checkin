import {router} from 'expo-router';
import {Plan} from '../domain/model';
import {weeklyStatistics,ruleValue} from '../domain/rules';
import {useApp} from '../state/AppProvider';
import {openRecord} from './shared';
import {TodayView,byName,walk,materialize,actionsByName} from '../ui/screens/TodayView';
import {documentByTitle} from '../ui/spec-documents';
import type {Inputs,NodeAction,SpecNode} from '../ui/spec-types';
export default function Today(){
 const app=useApp(),{snapshot}=app,sections=app.queries.today(snapshot).sections;
 for(const plan of [...sections.recorded]){const pin=app.pins[plan.id];if(pin&&pin.section!=='recorded'){sections.recorded=sections.recorded.filter(item=>item.id!==plan.id);const target=sections[pin.section as keyof typeof sections];target.splice(Math.min(pin.index,target.length),0,plan);}}
 const empty=!Object.values(sections).some(s=>s.length),doc=documentByTitle(empty?'01-':'02-');const inputs:Record<string,string|number>={'context.today':snapshot.today,'context.timeZoneLabel':snapshot.zone};
 const actions:Record<string,NodeAction>=actionsByName(doc,{'标题触控区域':{label:'设置',onPress:()=>router.push('/settings')},'＋ 创建第一个计划':{testID:'plan.create',onPress:()=>router.push('/plans/new')}});
 const body=byName(doc,'页面内容'),children:SpecNode[]=[];
 const heading=(name:string)=>children.push(byName(doc,name));
 const item=(plan:Plan,section:string,index:number)=>{
  const record=plan.type==='one_time'?snapshot.facts.one_time_results.find(row=>row.plan_id===plan.id&&row.business_on===snapshot.today):snapshot.facts.cycle_records.find(row=>row.plan_id===plan.id&&row.business_on===snapshot.today);
  const navigate=(result?:string)=>{app.pin(plan.id,section,index);openRecord(plan,snapshot.today,record?.id,result);};
  const week=plan.type==='weekly'?weeklyStatistics(snapshot,plan).current:undefined;
  const template=byName(doc,record?'早起伸展已记录':plan.type==='weekly'?'运动周目标':plan.type==='one_time'?'截止事项摘要':plan.direction==='avoid'?'不喝奶茶卡片':'晨间阅读卡片');
  const values:Inputs={...inputs,'today.doPlanName':plan.name,'today.doScheduleLabel':'执行日','today.avoidPlanName':plan.name,'today.avoidScheduleLabel':'执行日','today.weeklyPlanName':plan.name,'weekly.completedDays':week?.success??0,'weekly.targetDays':week?.target??0,'weekly.remainingDays':Math.max(0,(week?.target??0)-(week?.success??0)),'weekly.progressRatio':week?.progress??0,'task.name':plan.name,'task.deadlineLabel':ruleValue<string>(snapshot.facts,plan.id,'due_on',snapshot.today)??'未设置截止日期','today.recordedPlanName':plan.name,'record.submittedTime':record?new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:snapshot.zone}).format(record.submitted_at_ms):'00:00','record.note':record?.note??''};
  const card=materialize(template,plan.id,values,body.id);for(const n of walk(card)){if(['✓ 完成','✓ 做到了'].includes(n.name))actions[n.id]={testID:'today.result.'+plan.id+'.success',onPress:()=>navigate('success')};else if(['× 未完成','× 发生了'].includes(n.name))actions[n.id]={testID:'today.result.'+plan.id+'.failure',onPress:()=>navigate('failure')};else if(n.name==='— 跳过')actions[n.id]={testID:'today.result.'+plan.id+'.skip',onPress:()=>navigate('skip')};else if(n.name==='记录今天')actions[n.id]={testID:'record.new.'+plan.id,onPress:()=>navigate()};else if(n.name==='查看或修改记录')actions[n.id]={testID:'record.open.'+plan.id,onPress:()=>navigate()};}
  actions[card.id]={testID:plan.type==='one_time'?'record.new.'+plan.id:'plan.detail.'+plan.id,onPress:()=>plan.type==='one_time'?navigate('completed'):router.push({pathname:'/plans/[planId]',params:{planId:plan.id}})};children.push(card);
 };
 if(!empty){for(const key of ['fixed','weekly','once','recorded'] as const){if(!sections[key].length)continue;if(key==='fixed'){heading('需要处理标题');children.push(materialize(byName(doc,'需要处理说明'),'count',{'today.fixedPlanCount':sections.fixed.length},body.id));}else if(key==='weekly')heading('本周可记录标题');else if(key==='recorded')heading('已记录标题');sections[key].forEach((p,i)=>item(p,key,i));}}
 return <TodayView empty={empty} inputs={inputs} actions={actions} overrides={empty?undefined:{[body.id]:{...body,children}}} omitNavigation bottomSafeArea={false}/>;
}
