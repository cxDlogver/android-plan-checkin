import { useState } from 'react';
import { FlatList, View } from 'react-native';
import { router } from 'expo-router';
import { Status } from '../domain/model';
import { Cursor } from '../application/projections';
import { useApp } from '../state/AppProvider';
import { Button, Choice, Page } from '../ui/metal';
import { Empty, PlanCard } from './shared';

export default function Plans(){
  const {snapshot,queries}=useApp(),[filter,setFilter]=useState<Status>('running'),[cursors,setCursors]=useState<(Cursor|null)[]>([null]);
  const scope=`${filter}|${snapshot.today}|${snapshot.zone}|${snapshot.dataRevision}`;
  const [loadedScope,setLoadedScope]=useState(scope);
  const pages=(loadedScope===scope?cursors:[null]).map(cursor=>queries.plans(snapshot,filter,cursor));
  const items=pages.flatMap(page=>page.items),next=pages.at(-1)?.nextCursor;
  const load=()=>{if(!next)return;setLoadedScope(scope);setCursors(loadedScope===scope?[...cursors,next]:[null,next]);};
  return <Page title="计划" scroll={false} right={<Button title="新建" testID="plan.create" onPress={()=>router.push('/plans/new')}/>}><Choice value={filter} onChange={value=>{setFilter(value as Status);setCursors([null]);}} options={[{value:'running',label:'运行中'},{value:'paused',label:'暂停'},{value:'archived',label:'归档'}]}/><FlatList data={items} keyExtractor={plan=>plan.id} renderItem={({item:plan})=><View style={{marginBottom:16}}><PlanCard plan={plan}/></View>} ListFooterComponent={next?<Button title="加载更多计划" onPress={load}/>:null} ListEmptyComponent={<Empty>暂无{filter==='running'?'运行中':filter==='paused'?'暂停':'归档'}计划。</Empty>}/></Page>;
}
