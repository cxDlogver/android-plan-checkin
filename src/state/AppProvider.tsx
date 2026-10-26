import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppState, ActivityIndicator, Modal, View } from 'react-native';
import * as Crypto from 'expo-crypto';
import { now, attachReadInitialization } from '@verification/runtime';
import { AppService, bootstrap } from '../application/service';
import { CommandKind, CommandResult, Envelope, Snapshot } from '../domain/model';
import { businessToday } from '../domain/date';
import { Projections } from '../application/projections';
import { Button, Body } from '../ui/metal';

const messages:Record<string,string>={VALIDATION_FAILED:'请检查输入内容。',DAY_CHANGED:'业务日期已变化，请保留输入并重新确认日期与补记方式。',CONFIRMATION_STALE:'生效日期或状态已变化，请重新确认。',PLAN_CHANGED:'计划已变化，请加载最新状态后重新确认。',RECORD_CHANGED:'记录已变化，请查看最新记录后重新确认。',RECORD_EXISTS:'该日期已有记录，请进入现有记录。',DATE_INELIGIBLE:'这一天不符合该计划的记录条件。',OLD_STAGE:'这是旧执行阶段的日期，恢复后仍不能补记。',PAUSED:'计划已暂停，只能查看历史或申请恢复。',ARCHIVED:'计划已归档，全部记录只读。',READ_ONLY:'这条记录只读，不能修改或撤回。',TARGET_REMOVED:'目标已永久删除，请返回刷新列表。',COMMAND_ID_REUSED:'提交内容已变化，请重新确认。',COMMAND_EXPIRED:'提交已超过重试期限，请重新确认。',CLOCK_CHANGED:'设备时间已变化，请重新确认。',STORAGE_FULL:'存储空间不足，尚未确认保存。请释放空间后重试。',STORAGE_BUSY:'本机数据暂时不可用，尚未确认保存。请重试。',STORAGE_IO:'本机保存失败，尚未确认保存。原输入已保留，可重试。',SCHEMA_TOO_NEW:'数据版本高于当前应用支持版本，请安装兼容的新版本。',MIGRATION_FAILED:'数据升级失败，原数据已保留。可重试或安装兼容版本。',INIT_FAILED:'初始化失败，原数据已保留，请重试。'};
export const errorMessage=(code:string)=>messages[code]||messages.INIT_FAILED!;
export interface ContextValue { snapshot:Snapshot; service:AppService; queries:Projections; error:string|null; refresh:(clearPins?:boolean)=>Promise<Snapshot|undefined>; execute:(envelope:Envelope)=>Promise<CommandResult>; envelope:(kind:CommandKind,payload:Record<string,unknown>)=>Envelope; pins:Record<string,{section:string;index:number}>; pin:(planId:string,section:string,index:number)=>void; clearPins:()=>void }
const Context=createContext<ContextValue|null>(null);
export function AppScope({value,children}:{value:ContextValue;children:React.ReactNode}){return <Context.Provider value={value}>{children}</Context.Provider>;}
export function useApp(){const value=useContext(Context);if(!value)throw new Error('AppProvider required');return value;}
export function AppProvider({children}:{children:React.ReactNode}){
  const [service,setService]=useState<AppService|null>(null),[snapshot,setSnapshot]=useState<Snapshot|null>(null),[error,setError]=useState<string|null>(null),[attempt,setAttempt]=useState(0),[pins,setPins]=useState<ContextValue['pins']>({});
  const request=useRef(0),mounted=useRef(true),queries=useRef(new Projections());
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(()=>{let canceled=false;setError(null);bootstrap().then(async next=>{const current=await next.snapshot();if(!canceled){setService(next);setSnapshot(current);}}).catch(failure=>{if(!canceled)setError(failure?.code||'INIT_FAILED');});return()=>{canceled=true;};},[attempt]);
  const refresh=useCallback(async(clearPins=false)=>{if(!service)return;if(clearPins)setPins({});queries.current.invalidate();const sequence=++request.current;try{const current=await service.snapshot();if(mounted.current&&sequence===request.current){setSnapshot(current);setError(null);}return current;}catch(failure){if(mounted.current)setError((failure as {code?:string})?.code||'STORAGE_IO');}},[service]);
  useEffect(()=>{if(service)attachReadInitialization(async()=>{setSnapshot(null);await refresh();});},[service,refresh]);
  useEffect(()=>{if(!snapshot||!service)return;const listener=AppState.addEventListener('change',state=>{if(state==='active')void refresh();});const timer=setInterval(()=>{if(AppState.currentState==='active'&&businessToday(now(),snapshot.zone)!==snapshot.today)void refresh();},1000);return()=>{listener.remove();clearInterval(timer);};},[snapshot?.today,snapshot?.zone,service,refresh]);
  if(!snapshot||!service)return <View style={{flex:1,justifyContent:'center',padding:24,gap:20}}>{error?<><Body strong>{errorMessage(error)}</Body><Button title="重试初始化" testID="error.retry" onPress={()=>setAttempt(value=>value+1)}/></>:<><ActivityIndicator/><Body>正在加载本机数据…</Body></>}</View>;
  const value:ContextValue={service,queries:queries.current,snapshot,error,refresh,pins,pin:(planId,section,index)=>setPins(old=>({...old,[planId]:{section,index}})),clearPins:()=>setPins({}),envelope:(kind,payload)=>({commandId:Crypto.randomUUID(),issuedAtMs:now(),kind,payload}),execute:async command=>{if(error)return {ok:false,code:'STORAGE_IO'};const result=await service.execute(command);await refresh();return result;}};
  return <Context.Provider value={value}>{children}<Modal visible={!!error} transparent onRequestClose={()=>{}}><View style={{flex:1,justifyContent:'center',padding:20,backgroundColor:'#0008'}}><View style={{padding:20,gap:16,backgroundColor:'#FAFBFC'}}><Body title accessibilityRole="alert">无法读取本机数据</Body><Body>原数据和当前输入已保留。重新读取成功后才能继续操作。</Body><Button title="重试读取" testID="error.readRetry" onPress={()=>void refresh()}/></View></View></Modal></Context.Provider>;
}
