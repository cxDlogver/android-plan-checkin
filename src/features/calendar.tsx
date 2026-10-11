import { useState } from 'react';
import { FlatList, Pressable, View, useWindowDimensions } from 'react-native';
import { shiftMonth } from '../domain/date';
import { permission } from '../domain/rules';
import { useApp } from '../state/AppProvider';
import { Body, Button, Metal, Page, StatusFilter, colors } from '../ui/metal';
import { Empty, PlanCard, openRecord, resultText, resultColor } from './shared';

export default function Calendar({planId}:{planId?:string}){
  const {snapshot,queries}=useApp(),[month,setMonth]=useState(snapshot.today.slice(0,7)),[selected,setSelected]=useState(snapshot.today),[filter,setFilter]=useState('all');
  const {width,fontScale}=useWindowDimensions(),edge=width<380?4:20,cellWidth=(width-edge*2-4-12)/7,large=fontScale>=1.6;
  const projection=planId&&!snapshot.facts.plans.some(p=>p.id===planId)?null:queries.calendar(snapshot,month,selected,planId);
  if(!projection)return <Page title="计划日历" back><Empty>目标已永久删除。</Empty></Page>;
  const all=projection.items,completed=all.filter(item=>item.completed).length;
  const visible=all.filter(item=>filter==='all'||filter==='completed'&&item.completed||filter==='incomplete'&&!item.completed);
  const select=(on:string)=>{setSelected(on);setFilter('all');};
  const today=()=>{setMonth(snapshot.today.slice(0,7));select(snapshot.today);};
  const header=<View style={{gap:16}}>
    <Metal style={{marginHorizontal:edge-20,padding:0,paddingVertical:16}}>
      <View style={{paddingHorizontal:16,gap:12}}><View style={{flexDirection:'row',alignItems:'center',gap:8}}><Button title="‹" accessibilityLabel="上个月" testID="calendar.month.previous" onPress={()=>setMonth(shiftMonth(month,-1,snapshot.zone))}/><Body strong style={{flex:1,textAlign:'center'}}>{month}</Body><Button title="›" accessibilityLabel="下个月" testID="calendar.month.next" onPress={()=>setMonth(shiftMonth(month,1,snapshot.zone))}/></View><Button title="回今天" testID="calendar.today" onPress={today}/></View>
      <View style={{paddingHorizontal:2,flexDirection:'row',gap:2}}>{['一','二','三','四','五','六','日'].map(day=><Body key={day} style={{width:cellWidth,textAlign:'center',fontSize:12}}>{day}</Body>)}</View>
      <View style={{paddingHorizontal:2,flexDirection:'row',flexWrap:'wrap',columnGap:2}}>{projection.days.map(cell=>{
        const current=cell.on===snapshot.today,future=cell.on>snapshot.today;
        const label=cell.on+'，'+(current?'今天，':future?'未来，只读，':'')+(current?'':'完成'+cell.completed+'，共'+cell.total+'，')+(selected===cell.on?'已选中':'');
        const fraction=large?cell.label.replace('/','/\n'):cell.label;
        return <Pressable key={cell.on} accessibilityRole="button" accessibilityLabel={label} accessibilityState={{selected:selected===cell.on}} testID={'calendar.date.'+cell.on} onPress={()=>select(cell.on)} style={{width:cellWidth,minHeight:large?104:70,paddingVertical:8,alignItems:'center',backgroundColor:current?'#E0E6EB':'transparent',borderWidth:selected===cell.on?1:0,borderColor:colors.primary,opacity:cell.on.slice(0,7)===month?1:.45}}><Body strong={current} style={{fontSize:12}}>{Number(cell.on.slice(-2))}</Body><Body strong style={{fontSize:10,textAlign:'center',color:cell.label==='✓'?colors.success:colors.gold}}>{fraction}</Body></Pressable>;
      })}</View>
    </Metal>
    <Body title>{selected} · {all.length} 项计划</Body>
    <StatusFilter value={filter} onChange={setFilter} counts={{all:all.length,completed,incomplete:all.length-completed}}/>
    {!visible.length&&<Empty>{!all.length?'该日没有执行项':filter==='completed'?'该日没有已完成项':'该日没有未完成项'}</Empty>}
  </View>;
  return <Page title={planId?'计划日历':'日历'} back={!!planId} scroll={false}><FlatList contentContainerStyle={{paddingHorizontal:20,paddingTop:8,paddingBottom:8}} data={visible} keyExtractor={item=>item.key} ListHeaderComponent={header} renderItem={({item})=><View style={{marginTop:16}}><PlanCard plan={item.plan}>{item.record?<><Body strong style={{color:resultColor('result'in item.record?item.record.result:item.record.outcome)}}>{resultText(item.plan,'result'in item.record?item.record.result:item.record.outcome)}</Body><Button title="查看记录" onPress={()=>openRecord(item.plan,selected,item.record?.id)}/></>:permission(snapshot,item.plan,selected).allowed?<Button title={selected===snapshot.today?'记录今天':'补记这一天'} onPress={()=>openRecord(item.plan,selected)}/>:<Body>未记录 · 此日期只可查看</Body>}</PlanCard></View>} ListFooterComponent={projection.weeklyBackfills.length?<View style={{gap:16,marginTop:24}}><Body title>可补记的每周计划</Body><Body>这些空日不计入日历总数。</Body>{projection.weeklyBackfills.map(plan=><PlanCard plan={plan} key={plan.id}><Button title="补记这一天" onPress={()=>openRecord(plan,selected)}/></PlanCard>)}</View>:null}/></Page>;
}
