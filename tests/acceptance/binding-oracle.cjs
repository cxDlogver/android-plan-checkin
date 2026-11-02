'use strict';
const assert=require('node:assert/strict');
// Independent mapping of the UI input contract; never import the application's presentation mapper.
function expectedInputs(frame){
 const c=frame.context,p=c.activeRole===null?null:c.activeRole==='draft'?c.draft:c.catalog[c.activeRole],r=c.record;
 const newForm=frame.scene.screen.startsWith('new-')||frame.scene.screen==='edit-plan',task=newForm?c.draft:c.catalog.task;
 const out={...c.presentation,'environment.time':c.environment.time,'context.today':c.clock.today,'context.timeZoneLabel':c.environment.timeZone,'app.version':c.environment.version,'stats.asOfDate':c.clock.today,
  'today.doPlanName':c.catalog.fixedDo.name,'today.avoidPlanName':c.catalog.avoid.name,'today.weeklyPlanName':c.catalog.weekly.name,'today.recordedPlanName':c.catalog.recorded.name,
  'plans.fixed.name':c.catalog.fixedDo.name,'plans.fixed.scheduleLabel':c.catalog.fixedDo.scheduleLabel,'plans.weekly.name':c.catalog.weekly.name,'plans.avoid.name':c.catalog.avoid.name,'plans.avoid.scheduleLabel':c.catalog.avoid.scheduleLabel,
  'task.name':task.name,'task.description':task.description,'task.deadline':task.deadline,'task.deadlineLabel':task.deadline,'task.createdDate':task.createdDate,'task.overdueDays':task.overdueDays,
  'record.date':r.date,'record.note':r.note,'record.submittedAt':r.submittedAt,'record.submittedTime':r.submittedAt.slice(11,16),'record.completedDate':r.completedDate,'originalRecord.note':c.originalRecord.note,'originalRecord.submittedAt':c.originalRecord.submittedAt,
  'calendar.month':c.calendar.month,'calendar.selectedDate':c.calendar.selectedDate,'calendar.rows.successA.planName':c.catalog.fixedDo.name,'calendar.rows.successA.note':'成功备注 '+c.runId,'calendar.rows.successB.planName':c.catalog.weekly.name,'calendar.rows.successB.note':'每周备注 '+c.runId,'calendar.rows.failed.planName':c.catalog.avoid.name,'calendar.rows.skipped.planName':c.catalog.recorded.name,'calendar.rows.skipped.note':'跳过备注 '+c.runId,'calendar.rows.missing.planName':c.catalog.fixedDo.name};
 if(p)Object.assign(out,{'plan.name':p.name,'plan.description':p.description,'plan.scheduleLabel':p.scheduleLabel,'plan.behaviorName':p.behaviorName,'plan.timeZone':p.timeZone,'plan.startDate':p.startDate,'plan.endDate':p.endDate});
 for(const kind of ['success','skipped','missing']){out['history.'+kind+'.date']=c.history[kind].date;out['history.'+kind+'.note']=c.history[kind].note;}
 return out;
}
function inspect(document,frame,seed){
 if(seed){assert.deepEqual(frame.context.catalog,seed.catalog,'Prepared catalog remains the same external input');assert.deepEqual(frame.context.environment,seed.environment,'Prepared environment input remains stable');assert.deepEqual(frame.context.clock,seed.clock,'Prepared clock input remains stable');}
 const expected=expectedInputs(frame),nodes=node=>[node,...node.children.flatMap(nodes)],comparisons=[];
 for(const node of nodes(document.tree))for(const key of Object.keys(node.content?.binding?.parameters??{})){
  assert.ok(Object.hasOwn(expected,key),'Independent input mapping missing: '+key);
  comparisons.push({nodeId:node.id,key,expected:expected[key],actual:frame.inputs[key]});assert.deepEqual(frame.inputs[key],expected[key],'Independent semantic binding '+key);
 }
 return comparisons;
}
module.exports={expectedInputs,inspect};
