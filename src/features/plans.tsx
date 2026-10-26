import { useState } from 'react';
import { FlatList, View } from 'react-native';
import { router } from 'expo-router';
import { Status } from '../domain/model';
import { Cursor } from '../application/projections';
import { useApp } from '../state/AppProvider';
import { Button, Choice, Page } from '../ui/metal';
import { Empty } from './shared';
import {PlansView} from '../ui/screens/PlansView';
import {byName,walk,materialize,literal,actionsByName} from '../ui/screens/TodayView';
import {documentByTitle} from '../ui/spec-documents';
import {ruleValue} from '../domain/rules';
import type {NodeAction,SpecNode} from '../ui/spec-types';

export default function Plans(){
  const {snapshot,queries}=useApp(),[filter,setFilter]=useState<Status>('running'),[cursors,setCursors]=useState<(Cursor|null)[]>([null]);
  const scope=`${filter}|${snapshot.today}|${snapshot.zone}|${snapshot.dataRevision}`;
  const [loadedScope,setLoadedScope]=useState(scope);
  const pages=(loadedScope===scope?cursors:[null]).map(cursor=>queries.plans(snapshot,filter,cursor));
  const items=pages.flatMap(page=>page.items),next=pages.at(-1)?.nextCursor;
  const load=()=>{if(!next)return;setLoadedScope(scope);setCursors(loadedScope===scope?[...cursors,next]:[null,next]);};
  const doc=documentByTitle('03-'),body=byName(doc,'页面内容'),actions:Record<string,NodeAction>=actionsByName(doc,{'标题触控区域':{testID:'plan.create',onPress:()=>router.push('/plans/new')},...Object.fromEntries([['running','运行中选项'],['paused','暂停选项'],['archived','归档选项']].map(([value,name])=>[name!,{testID:'plans.filter.'+value,selected:filter===value,onPress:()=>{setFilter(value as Status);setCursors([null]);}}]))});
  const choices=byName(doc,'选项'),overrides:Record<string,SpecNode>={};for(const [value,name] of [['running','运行中选项'],['paused','暂停选项'],['archived','归档选项']]){const n=byName(doc,name!);overrides[n.id]={...n,styleRef:filter===value?'s-3d9eec7358fb85e8':'s-17918eeb59c2274a'};}
  const children=[choices,...items.map(plan=>{const template=byName(doc,plan.type==='weekly'?'运动':plan.type==='one_time'?'提交报名材料':plan.direction==='avoid'?'不喝奶茶':'晨间阅读');const card=materialize(template,plan.id,{'plans.fixed.name':plan.name,'plans.fixed.scheduleLabel':'固定日期','plans.weekly.name':plan.name,'weekly.targetDays':ruleValue<number>(snapshot.facts,plan.id,'weekly_target',snapshot.today)??0,'plans.avoid.name':plan.name,'plans.avoid.scheduleLabel':'固定日期','task.name':plan.name,'task.deadline':ruleValue<string>(snapshot.facts,plan.id,'due_on',snapshot.today)??snapshot.today},body.id);actions[card.id]={testID:'plan.detail.'+plan.id,onPress:()=>router.push({pathname:'/plans/[planId]',params:{planId:plan.id}})};return card;}),byName(doc,'计划入口说明')];
  overrides[body.id]={...body,children};return <PlansView inputs={{}} actions={actions} overrides={overrides} slots={{...(next?{[byName(doc,'计划入口说明').id]:<Button title="加载更多计划" onPress={load}/>}:{ }),...(!items.length?{[body.id]:<View style={{gap:16}}><Choice value={filter} onChange={value=>{setFilter(value as Status);setCursors([null]);}} options={[{value:'running',label:'运行中'},{value:'paused',label:'暂停'},{value:'archived',label:'归档'}]}/><Empty>暂无{filter==='running'?'运行中':filter==='paused'?'暂停':'归档'}计划。</Empty></View>}:{})}} omitNavigation bottomSafeArea={false}/>;
}
