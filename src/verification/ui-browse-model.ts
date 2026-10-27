import {documentByTitle} from '../ui/spec-documents';
import type {SpecDocument} from '../ui/spec-types';
import {activePlan,presentationInputs,requireDocumentInputs,selectPlan,type UIContext,type Role} from './ui-data-context';

export type Screen='today-empty'|'today'|'plans'|'calendar'|'new-fixed'|'new-weekly'|'new-task'|'record'|'avoid-record'|'edit-record'|'backfill'|'fixed-detail'|'weekly-detail'|'task-detail'|'edit-plan'|'management'|'archive'|'delete'|'settings'|'not-saved'|'complete'|'readonly'|'date-changed';
export type Scene={screen:Screen;entry?:Scene};
export type UIResponse={outcome:{screen:'ordinary-return'|'not-saved'|'date-changed'}};
export type UITrace={name:string;input:unknown;output?:unknown};
export const screenDocuments:Record<Screen,string>={'today-empty':'01-',today:'02-',plans:'03-','new-fixed':'04-','new-weekly':'05-','new-task':'06-',record:'07-','avoid-record':'08-','edit-record':'09-',backfill:'10-',calendar:'11-','fixed-detail':'12-','weekly-detail':'13-','task-detail':'14-','edit-plan':'15-',management:'16-',archive:'17-',delete:'18-',settings:'19-','not-saved':'20-',complete:'21-',readonly:'22-','date-changed':'23-'};
type Intent='plans'|'calendar'|'today'|'new'|'settings'|'fixed'|'weekly'|'task'|'delete-menu'|'type-fixed'|'type-weekly'|'type-task'|'back'|'save-new'|'record-do'|'record-avoid'|'record-weekly'|'record-edit'|'save-record'|'edit'|'more'|'history-missing'|'history-success'|'calendar-success-a'|'calendar-success-b'|'calendar-missing'|'return-detail'|'archive-accept'|'delete-return'|'record-weekly-detail'|'complete'|'save-complete'|'backfill-save'|'retry'|'continue-edit'|'date-backfill'|'return-calendar';
// Controls are bound to their semantic UI actions. No requirement graph is loaded at runtime.
const controls:Record<Screen,Record<string,Intent>>={
 'today-empty':{'n-K5MyJx__dzQvc':'plans','n-K5MyJx__j2SSi':'calendar','n-tpMoY':'new','n-xamIE':'settings'},
 today:{'n-u0sT7m':'record-do','n-V4A7NA':'record-avoid','n-jvvCs__dzQvc':'plans','n-jvvCs__j2SSi':'calendar','n-dJOCR':'settings','n-ysJnL':'record-weekly','n-udfEY':'record-edit'},
 plans:{'n-Y0xjQ__j2SSi':'calendar','n-Y0xjQ__r6bQuo':'today','n-u37qD':'new','n-z6PkYB':'fixed','n-dwSqJ':'weekly','n-BCVLQ':'task','n-l5YyRW':'delete-menu'},
 calendar:{'n-oPknT__dzQvc':'plans','n-oPknT__r6bQuo':'today','n-AZb5w':'calendar-success-a','n-h1LRo5':'calendar-success-b','n-zhJjJ':'calendar-missing'},
 'new-fixed':{'n-Mz5h2':'type-weekly','n-uZr9s':'type-task','n-oONvI':'back','n-YTsxX':'save-new'},
 'new-weekly':{'n-zlmxt':'type-fixed','n-qiLet':'type-task','n-Npncn':'back','n-EvXu3':'save-new'},
 'new-task':{'n-G5BTyl':'type-fixed','n-hj4eE':'type-weekly','n-HKTZU':'back','n-EnAJe':'save-new'},
 record:{'n-d6FEHb':'back','n-s3Xk6I':'save-record'},
 'avoid-record':{'n-w8wrf':'back','n-B0Dhl':'return-detail'},
 'edit-record':{'n-PCL8Z':'back','n-pIR8l':'return-detail'},
 'fixed-detail':{'n-U5K4i':'back','n-O9pBu':'edit','n-CqwBt':'more','n-ybpkX':'history-missing','n-c4qgT':'history-success'},
 'weekly-detail':{'n-Xui5N':'back','n-WZ4zp':'more','n-T6zcp':'record-weekly-detail','n-hzcu5':'history-missing','n-HnGqh':'history-success'},
 'task-detail':{'n-kq0yM':'back','n-S55fyE':'more','n-rFWAe':'complete'},
 'edit-plan':{'n-P69atC':'back','n-UxJiG':'return-detail'},
 management:{'n-EejMq':'return-detail','n-ExzJE':'return-detail','n-i8Dl4':'return-detail','n-Kn0Gw':'back'},
 archive:{'n-rbUlk':'archive-accept','n-OWMgC':'back','n-cij3j':'back'},
 delete:{'n-fXYFn':'delete-return','n-BKwuo':'delete-return','n-a5ons':'delete-return'},
 settings:{'n-o3U0H':'back'},
 'not-saved':{'n-L2jMlr':'back','n-O8FUG':'continue-edit','n-sVBFL':'retry'},
 'date-changed':{'n-TEV7R':'back','n-qtC8r':'date-backfill','n-LzvY2':'return-calendar'},
 complete:{'n-Z8KVex':'back','n-MH4FG':'save-complete'},
 readonly:{'n-wpDJX':'return-calendar','n-GTvpR':'return-calendar'},
 backfill:{'n-i87kF':'back','n-P1YwV':'backfill-save'}
};
export class UIBrowseModel{
 scene:Scene={screen:'today-empty'};
 navigationSerial=0;
 trace:UITrace[]=[];
 private response:UIResponse|null=null;
 constructor(public context:UIContext){}
 get document():SpecDocument{return documentByTitle(screenDocuments[this.scene.screen]);}
 get inputs(){const inputs=presentationInputs(this.context,{newForm:this.scene.screen.startsWith('new-'),returnContext:this.scene.entry?.screen??''});requireDocumentInputs(this.document,inputs);return inputs;}
 get activeIdentity(){return {planId:this.context.activeRole===null?null:activePlan(this.context).id,recordId:this.context.activeRole===null?null:this.context.record.id};}
 get controlIds(){return Object.keys(controls[this.scene.screen]);}
 get pendingResponse(){return this.response!==null;}
 isMenu(id:string){return ['more','delete-menu'].includes(controls[this.scene.screen][id]??'');}
 queueResponse(response:UIResponse){if(this.response)throw Error('当前UI响应尚未消费');if(!['ordinary-return','not-saved','date-changed'].includes(response.outcome.screen))throw Error('无效UI响应');this.response=response;}
 clearResponse(){this.response=null;}
 private go(scene:Scene){this.scene=scene;if(scene.screen==='today-empty')this.context.activeRole=null;this.navigationSerial++;}
 private enter(screen:Screen){this.go({screen,entry:this.scene});}
 private back(){if(!this.scene.entry)throw Error('当前画面没有返回入口');this.go(this.scene.entry);}
 private select(role:Role){selectPlan(this.context,role);}
 private openRecord(role:Role,screen:Screen){this.select(role);this.enter(screen);}
 setInput(field:string,value:string){const p=activePlan(this.context);if((this.scene.screen.startsWith('new-')||this.scene.screen==='edit-plan')&&['plan.name','task.name','plan.description','task.description'].includes(field)){if(field.endsWith('.name'))p.name=value;else p.description=value;}else if(field==='record.note'&&['record','avoid-record','edit-record','backfill','complete'].includes(this.scene.screen))this.context.record.note=value;else throw Error('当前画面不可编辑该字段：'+field);this.trace.push({name:'input',input:{field,value}});}
 dispatch(id:string,selection?:string){const intent=controls[this.scene.screen][id];if(!intent)throw Error('当前画面没有该操作：'+id);const before=this.scene;this.trace.push({name:'control',input:{id,selection,scene:before}});
  switch(intent){
   case 'plans':case 'calendar':case 'today':this.go({screen:intent});break;
   case 'new':this.context.activeRole='draft';this.enter('new-fixed');break;
   case 'settings':this.enter('settings');break;
   case 'fixed':this.select('fixedDo');this.enter('fixed-detail');break;
   case 'weekly':this.select('weekly');this.enter('weekly-detail');break;
   case 'task':this.select('task');this.enter('task-detail');break;
   case 'delete-menu':if(selection!=='已归档计划的永久删除确认')throw Error('请选择明确的归档操作');this.select('archived');this.enter('delete');break;
   case 'more':if(selection!=='计划管理'&&selection!=='删除并保留历史')throw Error('请选择明确的管理操作');this.enter(selection==='计划管理'?'management':'archive');break;
   case 'type-fixed':case 'type-weekly':case 'type-task':this.go({screen:intent==='type-fixed'?'new-fixed':intent==='type-weekly'?'new-weekly':'new-task',entry:before.entry});break;
   case 'save-new':this.go({screen:'today'});break;
   case 'back':case 'return-detail':case 'continue-edit':this.back();break;
   case 'record-do':this.openRecord('fixedDo','record');break;
   case 'record-avoid':this.openRecord('avoid','avoid-record');break;
   case 'record-weekly':this.openRecord('weekly','record');break;
   case 'record-edit':this.openRecord('recorded','edit-record');break;
   case 'record-weekly-detail':this.select('weekly');this.enter('record');break;
   case 'save-record':{const response=this.response??{outcome:{screen:'ordinary-return' as const}};this.response=null;this.trace.push({name:'record-response',input:{...this.activeIdentity,note:this.context.record.note,date:this.context.record.date},output:response});if(response.outcome.screen==='ordinary-return')this.back();else this.enter(response.outcome.screen);break;}
   case 'retry':{const record=before.entry;if(!record?.entry)throw Error('反馈缺少原始记录入口');this.go(record.entry);break;}
   case 'edit':this.enter('edit-plan');break;
   case 'archive-accept':case 'delete-return':this.go({screen:'plans'});break;
   case 'history-missing':this.context.record={...this.context.history.missing};this.context.originalRecord={...this.context.record};this.enter('backfill');break;
   case 'history-success':this.context.record={...this.context.history.success};this.context.originalRecord={...this.context.record};this.enter('readonly');break;
   case 'calendar-success-a':case 'calendar-success-b':case 'calendar-missing':{this.select(intent==='calendar-success-b'?'weekly':'fixedDo');const r=this.context.record;r.date=this.context.calendar.selectedDate;r.note=intent==='calendar-success-a'?'成功备注 '+this.context.runId:intent==='calendar-success-b'?'每周备注 '+this.context.runId:'补记备注 '+this.context.runId;r.id=this.context.runId+':calendar:'+this.context.activeRole+':'+r.date;r.submittedAt=r.date+'T09:14:00Z';this.context.originalRecord={...r};this.enter(intent==='calendar-missing'?'backfill':'readonly');break;}
   case 'date-backfill':this.enter('backfill');break;
   case 'return-calendar':this.go({screen:'calendar'});break;
   case 'backfill-save':this.go({screen:'readonly',entry:{screen:'calendar'}});break;
   case 'complete':this.select('task');this.enter('complete');break;
   case 'save-complete':this.back();break;
  }
  this.trace.push({name:'present',input:{from:before,to:this.scene,activeIdentity:this.activeIdentity}});
 }
}
