'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createContext}=require('./context.cjs'),oracle=require('./browse-oracle.cjs');
module.exports=async({root,directory,adapter,model,graph,visual,seed})=>{
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'plan/ui-spec/manifest.json'))),documents=new Map(manifest.documents.filter(d=>d.kind==='screen').map(d=>{const doc=JSON.parse(fs.readFileSync(path.join(root,'plan/ui-spec',d.file)));return [doc.id,doc];}));
 const docId=state=>graph.states.find(s=>s.id===state).source.find(s=>s.kind==='ui').documentId;
 function shortest(start,unseen){const queue=[{state:start,steps:[]}],seen=new Set([start]);while(queue.length){const item=queue.shift();if(unseen.has(docId(item.state)))return item.steps;for(const edge of [...graph.transitions.filter(t=>t.from===item.state),...(item.state==='S01'?[]:[{to:'S01',restart:true}])])if(!seen.has(edge.to)){seen.add(edge.to);queue.push({state:edge.to,steps:[...item.steps,edge]});}}throw Error('A canonical screen is unreachable from permitted UI entries');}
 const results=[];
 for(let group=0;group<2;group++){
  const context=createContext({...seed.environment,today:seed.clock.today,runId:seed.runId+'-visual-'+group});
  context.presentation['weekly.progressRatio']=group;context.presentation['weekly.completedDays']=group*context.presentation['weekly.targetDays'];context.presentation['weekly.remainingDays']=(1-group)*context.presentation['weekly.targetDays'];
  if(group){for(const plan of Object.values(context.catalog)){plan.name='另一组名称 '+plan.name;plan.description='另一组独立描述 '+plan.description;}context.draft.name='另一组新建输入 '+context.draft.name;}
  await adapter.restart(context);let current='S01';const unseen=new Set(documents.keys()),frames=[],actions=[];
  while(unseen.size){
   const id=docId(current);
   if(unseen.has(id)){const doc=documents.get(id),name='visual-'+group+'-'+doc.title.slice(0,2),shot=await adapter.observe(name);oracle.matchesState(graph,current,shot.report);const inspected=visual.inspect(doc,shot.report,{xml:shot.evidence.source});frames.push({documentId:id,name,inspected,inputs:shot.report.inputs});unseen.delete(id);}
   if(!unseen.size)break;
   for(const edge of shortest(current,unseen)){if(edge.restart){await adapter.restart(context);actions.push({kind:'restart',state:'S01'});}else{const c=model.cases.find(c=>c.id==='TC-'+edge.id);assert.ok(c);await adapter.perform(c);await adapter.device.waitSource(x=>x.includes(documents.get(docId(edge.to)).tree.id));actions.push({transition:edge.id,from:edge.from,to:edge.to});}current=edge.to;}
  }
  assert.equal(frames.length,23);results.push({group,context,frames,actions});fs.writeFileSync(path.join(directory,'visual-page-coverage.json'),JSON.stringify({groups:results},null,2)+'\n');
 }
 return results;
};
