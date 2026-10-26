'use strict';
const assert=require('node:assert/strict');
async function executeRoute(model,states,adapter,{onVisit=async()=>{}}={}){
 const cases=new Map(model.cases.map(c=>[c.id,c])),initial=new Set(states.states.filter(s=>s.isInitial).map(s=>s.id));let previous=null;const observations=[];
 for(let index=0;index<model.coverage.sequence.length;index++){
  const c=cases.get(model.coverage.sequence[index]);const restart=!previous||previous.expected.stateId!==c.given.stateId;
  if(restart){assert.ok(c.kind!=='primary'||initial.has(c.given.stateId),'Only declared entry states may restart');await adapter.prepare(c);}
  const before=await adapter.given(c);assert.equal(before.ok,true,'Given did not hold: '+c.id);
  const action=await adapter.perform(c),after=await adapter.expected(c);const row={visitIndex:index,caseId:c.id,before,action,after};observations.push(row);await onVisit(row);assert.equal(after.ok,true,'Expected facts did not hold: '+c.id);previous=c;
 }
 return observations;
}
module.exports={executeRoute};
