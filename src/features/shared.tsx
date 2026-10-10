import { router } from 'expo-router';
import { View } from 'react-native';
import { CycleResult, Outcome, Plan } from '../domain/model';
import { ruleValue, status } from '../domain/rules';
import { useApp } from '../state/AppProvider';
import { Body, Button, Metal, colors } from '../ui/metal';

export const typeLabel={fixed:'固定星期',weekly:'每周目标',one_time:'一次性'};
export const statusLabel={running:'运行中',paused:'暂停',archived:'归档'};
export const resultText=(plan:Plan,result:CycleResult|Outcome)=>result==='success'?(plan.direction==='avoid'?'✓ 做到了，没有发生目标行为':'✓ 完成'):result==='failure'?(plan.direction==='avoid'?'× 发生了目标行为':'× 未完成'):result==='skip'?'— 跳过':result==='completed'?'✓ 完成':result==='failed'?'× 失败':'⊘ 取消';
export const resultColor=(result:string)=>result==='success'||result==='completed'?colors.success:result==='failure'||result==='failed'?colors.failure:result==='cancelled'?colors.muted:colors.skip;
export function openRecord(plan:Plan,on:string,recordId?:string,result?:string){router.push(recordId?{pathname:'/records/[recordId]',params:{recordId,planId:plan.id}}:{pathname:'/records/new',params:{planId:plan.id,businessOn:on,result}});}
export function PlanCard({plan,children}:{plan:Plan;children?:React.ReactNode}){const {snapshot}=useApp();return <Metal><Body title accessibilityRole="header" onPress={()=>router.push({pathname:'/plans/[planId]',params:{planId:plan.id}})}>{plan.name}</Body><Body style={{fontSize:12,color:colors.muted}}>{typeLabel[plan.type]} · {plan.direction==='do'?'要做':'不要做'} · {statusLabel[status(snapshot.facts,plan.id,snapshot.asOfMs)]}</Body>{plan.type==='one_time'&&<Body>截止 {ruleValue<string>(snapshot.facts,plan.id,'due_on',snapshot.today)}</Body>}{children}<Button title="查看计划" testID={`plan.detail.${plan.id}`} onPress={()=>router.push({pathname:'/plans/[planId]',params:{planId:plan.id}})}/></Metal>;}
export const Empty=({children}:{children:React.ReactNode})=><View style={{paddingVertical:40,gap:16}}><Body strong style={{textAlign:'center'}}>{children}</Body></View>;
