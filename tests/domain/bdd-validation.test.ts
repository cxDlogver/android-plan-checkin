import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { normalizeEnvelope } from '../../src/domain/commands';
import { DomainError } from '../../src/domain/model';
const base=()=>({planId:randomUUID(),name:'边界',description:'',type:'fixed',direction:'do',startsOn:'2026-10-09',endOn:null,weekdayMask:10});
const normalize=(kind:string,payload:unknown)=>normalizeEnvelope({commandId:randomUUID(),issuedAtMs:Date.parse('2026-10-09T04:00:00Z'),kind,payload});
const rejected=(fn:()=>unknown)=>assert.throws(fn,e=>e instanceof DomainError&&e.code==='VALIDATION_FAILED');
test('AC017 newline names rejected for create and edit; multiline descriptions allowed',()=>{
  for(const separator of ['\n','\r','\u2028','\u2029']){
    rejected(()=>normalize('CreatePlan',{...base(),name:`读${separator}书`}));
    rejected(()=>normalize('EditPlan',{planId:randomUUID(),expectedPlanRevision:1,changes:{name:`读${separator}书`},ruleConfirmations:[]}));
  }
  assert.equal(normalize('CreatePlan',{...base(),description:'说明\n第二行'}).payload.description,'说明\n第二行');
});
test('AC017 combining characters count separately and description/note boundaries',()=>{
  assert.equal(normalize('CreatePlan',{...base(),name:'e\u0301'.repeat(40)}).payload.name,'e\u0301'.repeat(40));
  rejected(()=>normalize('CreatePlan',{...base(),name:'e\u0301'.repeat(41)}));
  assert.equal(normalize('CreatePlan',{...base(),description:'😀'.repeat(1000)}).payload.description,'😀'.repeat(1000));
  rejected(()=>normalize('CreatePlan',{...base(),description:'😀'.repeat(1001)}));
  const record={planId:randomUUID(),expectedPlanRevision:1,recordId:randomUUID(),businessOn:'2026-10-09',result:'success',confirmedToday:'2026-10-09',confirmedEntryKind:'ordinary'};
  for(const note of ['', '😀'.repeat(2000)])assert.equal(normalize('SubmitCycleRecord',{...record,note}).payload.note,note);
  rejected(()=>normalize('SubmitCycleRecord',{...record,note:'😀'.repeat(2001)}));
});
test('AC020/021 mask upper bound and integer-only weekly target',()=>{
  rejected(()=>normalize('CreatePlan',{...base(),weekdayMask:128}));
  for(const weeklyTarget of [0,8,3.5])rejected(()=>normalize('CreatePlan',{...base(),type:'weekly',weekdayMask:undefined,weeklyTarget}));
  for(const weeklyTarget of [1,7])assert.equal(normalize('CreatePlan',{...base(),type:'weekly',weekdayMask:undefined,weeklyTarget}).payload.weeklyTarget,weeklyTarget);
});
