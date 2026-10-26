import {useState} from 'react';
import {router} from 'expo-router';
import {shiftMonth} from '../domain/date';
import {permission} from '../domain/rules';
import {useApp} from '../state/AppProvider';
import {Page,StatusFilter} from '../ui/metal';
import {Empty,openRecord} from './shared';
import {CalendarView} from '../ui/screens/CalendarView';
import {byName,walk,materialize,literal,actionsByName} from '../ui/screens/TodayView';
import {documentByTitle} from '../ui/spec-documents';
import type {NodeAction,SpecNode} from '../ui/spec-types';
export default function Calendar({planId}:{planId?:string}){
 const {snapshot,queries}=useApp(),[month,setMonth]=useState(snapshot.today.slice(0,7)),[selected,setSelected]=useState(snapshot.today),[filter,setFilter]=useState('all');
 const projection=planId&&!snapshot.facts.plans.some(p=>p.id===planId)?null:queries.calendar(snapshot,month,selected,planId);
 if(!projection)return <Page title="计划日历" back><Empty>目标已永久删除。</Empty></Page>;
 const all=projection.items,completed=all.filter(item=>item.completed).length,visible=all.filter(item=>filter==='all'||filter==='completed'&&item.completed||filter==='incomplete'&&!item.completed);
 const select=(on:string)=>{setSelected(on);setFilter('all');},today=()=>{setMonth(snapshot.today.slice(0,7));select(snapshot.today);};
 const doc=documentByTitle('11-'),grid=byName(doc,'日期七列网格'),details=byName(doc,'选日计划明细');const actions:Record<string,NodeAction>=actionsByName(doc,{'标题触控区域':{testID:planId?'calendar.back':'calendar.today',label:planId?'返回':'回今天',onPress:planId?()=>router.back():today},'上个月':{testID:'calendar.month.previous',onPress:()=>setMonth(shiftMonth(month,-1,snapshot.zone))},'下个月':{testID:'calendar.month.next',onPress:()=>setMonth(shiftMonth(month,1,snapshot.zone))}}),overrides:Record<string,SpecNode>={};
 const defaultCell=byName(doc,'日期1'),counter=byName(doc,'日期完成汇总 0/1');
 overrides[grid.id]={...grid,children:projection.days.map(cell=>{const n=materialize(defaultCell,cell.on,{'calendar.cells.c04.day':Number(cell.on.slice(-2))},grid.id);n.styleRef=selected===cell.on?'s-322d1e69a003e167':cell.on===snapshot.today?'s-335282d92395cb34':'s-5411396ba36ba791';if(cell.label&&cell.on!==snapshot.today)n.children.push({...literal(counter,cell.label),id:n.id+'.count',parentId:n.id});actions[n.id]={testID:'calendar.date.'+cell.on,label:cell.on+'，'+cell.label,selected:selected===cell.on,onPress:()=>select(cell.on)};return n;})};
 const row=(item:typeof visible[number])=>{const result=item.record?('result'in item.record?item.record.result:item.record.outcome):'missing';const template=byName(doc,result==='success'||result==='completed'?'晨间阅读明细':result==='failure'||result==='failed'?'不要吸烟明细':result==='skip'?'晚间拉伸明细':'喝水明细');const inputs=Object.fromEntries(['successA','successB','failed','skipped','missing'].flatMap(k=>[['calendar.rows.'+k+'.planName',item.plan.name],['calendar.rows.'+k+'.note',item.record?.note??'']]));const n=materialize(template,item.key,inputs,details.id);for(const child of walk(n).filter(c=>c.name.endsWith('说明')))overrides[child.id]=literal(child,item.record?(item.record.note?item.record.note+' · ':'')+(selected===snapshot.today?'可查看或修改':'历史只读'):permission(snapshot,item.plan,selected).allowed?(selected===snapshot.today?'记录今天':'有效日期，可补记'):'未记录 · 此日期只可查看');if(item.record||permission(snapshot,item.plan,selected).allowed)actions[n.id]={testID:'calendar.record.'+item.key,onPress:()=>openRecord(item.plan,selected,item.record?.id)};return n;};
 const rows=visible.map(row);for(const plan of projection.weeklyBackfills){const n=materialize(byName(doc,'喝水明细'),plan.id,{'calendar.rows.missing.planName':plan.name},details.id);actions[n.id]={testID:'calendar.backfill.'+plan.id,onPress:()=>openRecord(plan,selected)};rows.push(n);}overrides[details.id]={...details,children:rows};
 if(planId){const title=byName(doc,'页面标题');overrides[title.id]=literal(title,'计划日历');}
 return <CalendarView inputs={{'calendar.month':month+'-01','calendar.selectedDate':selected,'calendar.selectedPlanCount':all.length,'calendar.filteredPlanCount':visible.length}} actions={actions} overrides={overrides} slots={{[byName(doc,'完成状态筛选框').id]:<StatusFilter value={filter} onChange={setFilter} counts={{all:all.length,completed,incomplete:all.length-completed}}/>,...(!visible.length?{[details.id]:<Empty>{!all.length?'该日没有执行项':filter==='completed'?'该日没有已完成项':'该日没有未完成项'}</Empty>}:{})}} omitNavigation bottomSafeArea={!!planId}/>;
}
