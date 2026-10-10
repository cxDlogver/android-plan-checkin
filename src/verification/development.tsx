import { useEffect, useState } from 'react';
import { View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { DateTime } from 'luxon';
import * as Application from 'expo-application';
import { useApp } from '../state/AppProvider';
import { Body, Button, Choice, Field, Metal, Notice, Page, confirm } from '../ui/metal';
import { businessToday, validZone } from '../domain/date';
import { setMeta } from '../domain/model';
import { loadFacts, persist } from '../infrastructure/database/executor';
import { now, setClock, injectFault, verificationExecutor } from './runtime-development';
import { buildFixture, fixtureNames, FixtureName } from './fixtures';

export default function VerificationScreen(){
  const app=useApp(),{service}=app,[report,setReport]=useState<Record<string,unknown>|null>(null),progress=useSharedValue(0);
  const [instant,setInstant]=useState(DateTime.fromMillis(now()).toUTC().toISO()||''),[zone,setZone]=useState(app.snapshot.zone),[fixture,setFixture]=useState<FixtureName>('F01'),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const isolated=Application.applicationId==='com.xiang.plancheckin.dev';
  async function capture(){const sqlite=await service.diagnostics(),snapshot=await service.snapshot();setReport({scope:'native-module-sample',sqlite,snapshot:fixture==='PERF'?{...snapshot,facts:Object.fromEntries(Object.entries(snapshot.facts).map(([name,rows])=>[name,{count:rows.length}]))}:snapshot});}
  async function seed(){if(!isolated||busy)return;if(!validZone(zone)){setMessage('请输入有效IANA时区。');return;}if(!await confirm('重置隔离开发库',`清空.dev库，载入 ${fixture}；固定时区重置为 ${zone}。不操作正式应用私有库。`,true))return;setBusy(true);injectFault(null);try{const executor=verificationExecutor();await executor.queue(tx=>executor.transaction(tx,async()=>{const before=await loadFacts(tx),facts=buildFixture(fixture,businessToday(now(),zone),zone);setMeta(facts,'data_revision',String(Number(before.app_meta.find(m=>m.key==='data_revision')?.value||0)+1));await persist(tx,before,facts);}));await app.refresh(true);await capture();setMessage(`${fixture} 已载入。`);}catch{setMessage('夹具载入失败，事务已回滚。');}finally{setBusy(false);}}
  const animation=useAnimatedStyle(()=>({transform:[{translateX:progress.value}]}));
  useEffect(()=>{service.diagnostics().then(sqlite=>{const ny=DateTime.fromISO('2026-03-08',{zone:'America/New_York'}),shanghai=DateTime.fromISO('2026-10-09',{zone:'Asia/Shanghai'});setReport({scope:'native-module-sample',sqlite,intl:{shanghai:shanghai.toISODate(),newYork:ny.plus({days:1}).toISODate(),dstHours:ny.plus({days:1}).diff(ny,'hours').hours}});});},[service]);
  return <Page title="原生模块验证" back><Metal><Body style={{fontFamily:'NotoSC400'}}>计划打卡 中文字体 400</Body><Body style={{fontFamily:'NotoSC600'}}>计划打卡 中文字体 600</Body><Body style={{fontFamily:'NotoSC700'}}>计划打卡 中文字体 700</Body></Metal><Button title="验证动画" testID="native.animation" onPress={()=>{progress.value=withTiming(progress.value===0?120:0);}}/><View style={{height:40}}><Animated.View style={[{width:30,height:30,backgroundColor:'#006E3A'},animation]}/></View>
    {isolated?<Metal><Body title>隔离验收控制</Body><Field label="测试瞬间（ISO，必须包含Z或时差）" value={instant} onChangeText={setInstant} testID="native.clock.input"/><Button title="应用测试时钟" testID="native.clock.apply" onPress={async()=>{const parsed=DateTime.fromISO(instant,{setZone:true});if(!parsed.isValid||!/(Z|[+-]\d{2}:\d{2})$/.test(instant)){setMessage('请输入带明确时差的有效ISO瞬间。');return;}setClock(parsed.toMillis());await app.refresh(true);setMessage(`测试时钟：${instant}`);}}/><Button title="恢复系统时钟" testID="native.clock.system" onPress={async()=>{setClock(null);await app.refresh(true);setMessage('已恢复系统时钟。');}}/><Field label="夹具固定IANA时区（只重置.dev库）" value={zone} onChangeText={setZone} testID="native.fixture.zone"/><Choice value={fixture} onChange={value=>setFixture(value as FixtureName)} options={fixtureNames.map(value=>({value,label:value}))} testID="native.fixture"/><Button title={busy?'正在载入…':'清空.dev并载入夹具'} disabled={busy} testID="native.fixture.load" onPress={()=>void seed()}/><Button title="下一次COMMIT前失败（一次）" testID="native.fault.beforeCommit" onPress={()=>{injectFault('before_commit');setMessage('已设置一次COMMIT前故障。');}}/><Button title="下一次用户保存成功后丢失返回（一次）" testID="native.fault.afterCommit" onPress={()=>{injectFault('after_commit');setMessage('已设置一次成功后返回丢失。');}}/><Button title="取消故障" testID="native.fault.clear" onPress={()=>{injectFault(null);setMessage('故障已清除。');}}/><Button title="读回当前事实与参数" testID="native.snapshot" onPress={()=>void capture()}/>{!!message&&<Notice>{message}</Notice>}</Metal>:<Notice>测试控制仅允许开发包身份。</Notice>}
    <Body testID="native.report" accessibilityLabel={JSON.stringify(report)} selectable>{JSON.stringify(report,null,2)||'正在读取原生参数…'}</Body></Page>;
}
