'use strict';
const {randomUUID}=require('node:crypto');
const shift=(date,days)=>new Date(Date.parse(date+'T00:00:00Z')+days*86400000).toISOString().slice(0,10);
function createContext({today,time,timeZone,version,runId='acceptance-'+randomUUID().slice(0,8)}){
 const roles=['fixedDo','avoid','weekly','task','recorded','archived'];
 const labels=['阅读安排','减少甜食','户外活动','学习资料','晚间记录','归档安排'];
 const catalog=Object.fromEntries(roles.map((role,index)=>[role,{id:runId+':'+role,name:labels[index]+' '+runId,description:'独立场景输入 '+runId,scheduleLabel:role==='weekly'?'每周目标 · 4 天':'固定日期 · 每天',behaviorName:labels[index],timeZone,startDate:shift(today,-30),endDate:shift(today,50),deadline:shift(today,-2),createdDate:shift(today,-8),overdueDays:2}]));
 const first=today.slice(0,7)+'-01',weekday=new Date(first+'T00:00:00Z').getUTCDay(),firstDate=shift(first,-((weekday+6)%7));
 const record={id:runId+':record:fixedDo',planId:catalog.fixedDo.id,date:today,note:'独立记录输入 '+runId,submittedAt:today+'T08:23:00Z',completedDate:today};
 const history=Object.fromEntries(['success','skipped','missing'].map((kind,index)=>[kind,{...record,id:runId+':history:'+kind,date:shift(today,-index-1),note:'历史'+kind+' '+runId}]));
 const presentation={'today.fixedPlanCount':3,'today.doScheduleLabel':catalog.fixedDo.scheduleLabel,'today.avoidScheduleLabel':catalog.avoid.scheduleLabel,'weekly.completedDays':2,'weekly.targetDays':4,'weekly.remainingDays':2,'weekly.progressRatio':.5,'calendar.selectedPlanCount':5,'calendar.filteredPlanCount':1,'stats.completionRate':.75,'stats.successCount':9,'stats.totalCount':12,'stats.skippedCount':2,'stats.missingCount':1,'stats.streakDays':3,'stats.weekCompletionRate':.6,'stats.completedWeeks':3,'stats.totalWeeks':5,'stats.streakWeeks':2};
 for(let index=1;index<=35;index++)presentation['calendar.cells.c'+String(index).padStart(2,'0')+'.day']=Number(shift(firstDate,index-1).slice(-2));
 for(const [index,completed,total]of [[9,1,3],[10,2,4],[11,3,5]]){const key='calendar.cells.c'+String(index).padStart(2,'0');presentation[key+'.completed']=completed;presentation[key+'.total']=total;}
 return {runId,environment:{time,timeZone,version},clock:{today},catalog,draft:{...catalog.fixedDo,id:runId+':draft',name:'新安排 '+runId,description:'独立草稿 '+runId,deadline:shift(today,12)},activeRole:null,record,originalRecord:{...record},history,calendar:{month:first,firstDate,selectedDate:shift(firstDate,10)},presentation};
}
module.exports={createContext,shift};
