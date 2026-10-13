import { router } from 'expo-router';
import { SectionList, View } from 'react-native';
import { Plan } from '../domain/model';
import { weeklyStatistics } from '../domain/rules';
import { formatDate } from '../domain/date';
import { useApp, errorMessage } from '../state/AppProvider';
import { Body, Button, Choice, Notice, Page, MetaLine, SettingsButton, colors } from '../ui/metal';
import { Empty, PlanCard, openRecord, resultText, resultLabel, resultColor } from './shared';

export default function Today(){
  const app=useApp(),{snapshot}=app,sections=app.queries.today(snapshot).sections;
  for(const plan of [...sections.recorded]){const pin=app.pins[plan.id];if(pin&&pin.section!=='recorded'){sections.recorded=sections.recorded.filter(item=>item.id!==plan.id);const target=sections[pin.section as keyof typeof sections];target.splice(Math.min(pin.index,target.length),0,plan);}}
  const labels={fixed:'需要处理',weekly:'本周可记录',once:'截止事项',recorded:'已记录'};
  const data=(Object.keys(sections) as (keyof typeof sections)[]).map(key=>({key,title:labels[key],data:sections[key]}));
  const item=(plan:Plan,section:string,index:number)=>{
    const record=plan.type==='one_time'?snapshot.facts.one_time_results.find(row=>row.plan_id===plan.id&&row.business_on===snapshot.today):snapshot.facts.cycle_records.find(row=>row.plan_id===plan.id&&row.business_on===snapshot.today);
    const navigate=(result?:string)=>{app.pin(plan.id,section,index);openRecord(plan,snapshot.today,record?.id,result);};
    const week=plan.type==='weekly'?weeklyStatistics(snapshot,plan).current:undefined;
    return <View style={{marginBottom:16}}><PlanCard plan={plan}>{record?<><Body strong style={{color:resultColor('result'in record?record.result:record.outcome)}}>{resultText(plan,'result'in record?record.result:record.outcome)} · 已保存</Body>{!!record.note&&<Body>{record.note}</Body>}<Button title="查看或修改记录" testID={`record.open.${plan.id}`} onPress={()=>navigate()}/></>:plan.type==='weekly'?<><Body>本周 {week?.success||0}/{week?.target||0} 天{week?.partialReason?` · ${week.partialReason}`:''}</Body><View style={{height:7,backgroundColor:colors.border}}><View style={{height:7,width:`${(week?.progress||0)*100}%`,backgroundColor:colors.primary}}/></View><Button title="记录今天" testID={`record.new.${plan.id}`} onPress={()=>navigate()}/></>:plan.type==='one_time'?<Button title="登记结果" testID={`record.new.${plan.id}`} onPress={()=>navigate('completed')}/>:<Choice value="" options={['success','failure','skip'].map(result=>({value:result,label:resultLabel(plan,result as 'success'|'failure'|'skip'),accessibilityLabel:resultText(plan,result as 'success'|'failure'|'skip'),color:resultColor(result)}))} onChange={navigate} testID={`today.result.${plan.id}`}/>}</PlanCard></View>;
  };
  return <Page title="今日" scroll={false} right={<SettingsButton onPress={()=>router.push('/settings')}/>} ><SectionList contentContainerStyle={{paddingHorizontal:20,paddingTop:8,paddingBottom:8}} sections={data} keyExtractor={plan=>plan.id} stickySectionHeadersEnabled={false} renderItem={({item:plan,section,index})=>item(plan,section.key,index)} renderSectionHeader={({section})=>section.data.length?<Body section style={{marginVertical:16}}>{section.title} · {section.data.length}</Body>:null} ListHeaderComponent={<View style={{gap:16,paddingBottom:8}}><MetaLine parts={[formatDate(snapshot.today,snapshot.zone),snapshot.zone]}/>{app.error&&<Notice error>{errorMessage(app.error)}</Notice>}<View style={{flexDirection:'row',gap:8}}><View style={{flex:1}}><Button title="新建计划" testID="plan.create" onPress={()=>router.push('/plans/new')}/></View><Button title="刷新" onPress={()=>void app.refresh(true)}/></View>{!data.some(section=>section.data.length)&&<Empty>今天还没有可记录的计划。{snapshot.facts.plans.length?'可前往计划页查看未来或暂停的计划。':'从一个小计划开始。'}</Empty>}</View>}/></Page>;
}
