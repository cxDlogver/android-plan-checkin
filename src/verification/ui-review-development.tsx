import React,{useCallback,useRef,useState} from 'react';
import {Alert,BackHandler,Keyboard,Pressable,TextInput,View,PixelRatio} from 'react-native';
import * as Application from 'expo-application';
import * as Font from 'expo-font';
import {AppScope,useApp} from '../state/AppProvider';
import {TodayView,walk} from '../ui/screens/TodayView';
import {PlansView} from '../ui/screens/PlansView';
import {CalendarView} from '../ui/screens/CalendarView';
import {PlanFormView} from '../ui/screens/PlanFormView';
import {RecordFormView} from '../ui/screens/RecordFormView';
import {RecordFeedbackView} from '../ui/screens/RecordFeedbackView';
import {PlanDetailView} from '../ui/screens/PlanDetailView';
import {PlanManagementView} from '../ui/screens/PlanManagementView';
import {SettingsView} from '../ui/screens/SettingsView';
import {uiVersion} from '../ui/spec-documents';
import {useRenderEnvironment} from '../ui/spec-renderer';
import type {NodeAction,MeasuredNode,SpecNode} from '../ui/spec-types';
import {createUIContext,type UIContext} from './ui-data-context';
import {UIBrowseModel,type UIResponse} from './ui-browse-model';

function initialContext(){const date=new Date(),zone=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC',parts=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date),get=(type:string)=>parts.find(p=>p.type===type)!.value;return createUIContext('预览-'+date.getTime().toString(36),{time:date.toTimeString().slice(0,5),timeZone:zone,version:(Application.nativeApplicationVersion??'未知版本')+'（'+(Application.nativeBuildVersion??'未知构建')+'）'},get('year')+'-'+get('month')+'-'+get('day'));}
export default function UIReview({onClose}:{onClose:()=>void}){
 const parent=useApp(),environment=useRenderEnvironment(),insets=environment.insets,window=environment.window,keyboard=environment.keyboard,model=useRef(new UIBrowseModel(initialContext())),measurements=useRef<Record<string,MeasuredNode>>({}),[revision,setRevision]=useState(0),[report,setReport]=useState(''),[command,setCommand]=useState(''),boundaryCalls=useRef<unknown[]>([]),captureSerial=useRef(0),epoch=useRef(0);
 const guard=useCallback((name:string,...args:unknown[])=>{boundaryCalls.current.push({name,args});throw Error('UI浏览禁止调用业务执行：'+name);},[]);
 const scope={...parent,execute:((...args:unknown[])=>guard('execute',...args)) as typeof parent.execute,service:new Proxy(parent.service,{get(target,key){if(['execute','seed','persist','write'].includes(String(key)))return (...args:unknown[])=>guard('service.'+String(key),...args);return Reflect.get(target,key);}})};
 const measure=useCallback((node:MeasuredNode)=>{const prior=measurements.current[node.id];measurements.current[node.id]={...prior,...node,props:node.props??prior?.props,text:node.text??prior?.text,lines:node.lines??prior?.lines};},[]);
 const refresh=()=>setRevision(n=>n+1);
 const invoke=(id:string,selection?:string)=>{const before=model.current.navigationSerial;model.current.dispatch(id,selection);if(before!==model.current.navigationSerial)measurements.current={};Keyboard.dismiss();refresh();};
 React.useEffect(()=>{const back=BackHandler.addEventListener('hardwareBackPress',()=>{onClose();return true;});return()=>{back.remove();model.current.clearResponse();};},[onClose]);
 const capture=(nonce:string)=>{const m=model.current;setReport(JSON.stringify({nonce,revision,navigationSerial:m.navigationSerial,uiVersion,documentId:m.document.id,scene:m.scene,inputs:m.inputs,activeIdentity:m.activeIdentity,context:m.context,trace:m.trace,boundaryCalls:boundaryCalls.current,pendingResponse:m.pendingResponse,measurements:window.width>=768?{}:measurements.current,environment:{viewport:environment.viewport,window:{width:window.width,height:window.height},rawInsets:environment.rawInsets,fontScale:window.fontScale,pixelRatio:PixelRatio.get(),insets,keyboard},fonts:Object.fromEntries(['NotoSC400','NotoSC600','NotoSC700','Inter400','Inter600','Inter700'].map(name=>[name,Font.isLoaded(name)]))}));};
 const receive=(value:string)=>{setCommand(value);if(!value.endsWith('\n'))return;try{const c=JSON.parse(value.trim());if(c.type==='capture')capture(String(c.nonce));else if(c.type==='response'){model.current.queueResponse(c.response as UIResponse);refresh();}else if(c.type==='configure'){if(model.current.scene.screen!=='today-empty'||model.current.trace.length)throw Error('只有初始入口可以设置本段输入');const context=c.context as UIContext;if(!context.runId||!context.catalog||context.activeRole!==null)throw Error('无效浏览数据');model.current=new UIBrowseModel(context);epoch.current++;measurements.current={};refresh();}else if(c.type==='restart'){model.current=new UIBrowseModel(initialContext());epoch.current++;measurements.current={};boundaryCalls.current=[];refresh();}else if(c.type==='close')onClose();else throw Error('不支持的浏览命令');}catch(error){setReport(JSON.stringify({error:String(error)}));}setCommand('');};
 const m=model.current,doc=m.document,nodes=walk(doc.tree),byId=new Map(nodes.map(n=>[n.id,n])),actions:Record<string,NodeAction>={};
 for(const id of m.controlIds){const original=byId.get(id);if(!original)throw Error('浏览控件不在页面结构中：'+id);let node:SpecNode=original;if(node.kind==='vector'&&node.parentId)node=byId.get(node.parentId)!;actions[node.id]={accessible:false,onPress:()=>{if(m.isMenu(id)){const archived=m.scene.screen==='plans';Alert.alert(archived?'归档计划':'更多管理操作',undefined,archived?[{text:'已归档计划的永久删除确认',onPress:()=>invoke(id,'已归档计划的永久删除确认')},{text:'取消',style:'cancel'}]:[{text:'计划管理',onPress:()=>invoke(id,'计划管理')},{text:'删除并保留历史',onPress:()=>invoke(id,'删除并保留历史')},{text:'取消',style:'cancel'}]);}else invoke(id);}};}
 for(const node of nodes){const b=node.content?.binding;if(node.kind!=='text'||!b||!node.name.endsWith('内容'))continue;const fields=Object.keys(b.parameters),field=fields.length===1?fields[0]:undefined;if(!field)continue;const form=m.scene.screen.startsWith('new-')||m.scene.screen==='edit-plan',record=['record','avoid-record','edit-record','backfill','complete'].includes(m.scene.screen);if((form&&['plan.name','task.name','plan.description','task.description'].includes(field))||(record&&field==='record.note'))actions[node.id]={input:{value:String(m.inputs[field]),label:node.name,multiline:node.content!.wrap==='wrap',onChange:value=>{m.setInput(field,value);refresh();}}};}
 const options={inputs:m.inputs,actions,onMeasure:measure},screen=m.scene.screen;
 let view:React.ReactNode;
 if(screen==='today'||screen==='today-empty')view=<TodayView empty={screen==='today-empty'} {...options}/>;
 else if(screen==='plans')view=<PlansView {...options}/>;
 else if(screen==='calendar')view=<CalendarView {...options}/>;
 else if(screen.startsWith('new-')||screen==='edit-plan')view=<PlanFormView document={doc} {...options}/>;
 else if(screen.endsWith('-detail'))view=<PlanDetailView document={doc} {...options}/>;
 else if(['management','archive','delete'].includes(screen))view=<PlanManagementView kind={screen==='management'?'manage':screen==='archive'?'archive':'delete'} {...options}/>;
 else if(screen==='settings')view=<SettingsView {...options}/>;
 else if(screen==='not-saved'||screen==='date-changed')view=<RecordFeedbackView dateChanged={screen==='date-changed'} {...options}/>;
 else view=<RecordFormView document={doc} {...options}/>;
 const chunks=report.match(/[\s\S]{1,12000}/g)??[];
 return <AppScope value={scope}><View style={{flex:1}}><View key={epoch.current+'-'+m.navigationSerial} style={{flex:1}}>{view}</View><Pressable testID="ui-review.capture" onPress={()=>capture(String(++captureSerial.current))} style={{position:'absolute',left:0,top:76,width:2,height:2,opacity:.01}}/><TextInput testID="ui-review.command" value={command} onChangeText={receive} showSoftInputOnFocus={false} caretHidden autoCorrect={false} multiline style={{position:'absolute',left:0,top:80,width:2,height:2,padding:0,color:'transparent',backgroundColor:'transparent',opacity:.01}}/><View testID="ui-review.report" accessible accessibilityLabel={JSON.stringify({chunks:chunks.length,revision})} style={{position:'absolute',left:0,top:82,width:1,height:1}}/>{chunks.map((chunk,i)=><View key={i} testID={'ui-review.chunk.'+i} accessible accessibilityLabel={chunk} style={{position:'absolute',left:0,top:83+i,width:1,height:1}}/>)}</View></AppScope>;
}
