import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {applyCommand,normalizeEnvelope,reconcile} from '../../src/domain/commands';
import {dayMs} from '../../src/domain/date';
import {DomainError,emptyFacts,setMeta} from '../../src/domain/model';
const zone='Asia/Shanghai',ms=(on:string)=>dayMs(on,zone)+12*3600000;
for(const type of ['fixed','one_time'] as const)test(`AC054 cross-day ${type} first submission reports DAY_CHANGED before stale plan revision`,()=>{
 const planId=randomUUID(),base=emptyFacts();setMeta(base,'app_timezone',zone);setMeta(base,'data_revision','0');
 const create=normalizeEnvelope({commandId:randomUUID(),issuedAtMs:ms('2026-10-09'),kind:'CreatePlan',payload:{planId,name:'跨日出口',description:'',type,direction:'do',...(type==='fixed'?{startsOn:'2026-10-09',endOn:'2026-10-09',weekdayMask:127}:{dueOn:'2026-10-09'})}});
 let facts=applyCommand(base,create,ms('2026-10-09'),zone,randomUUID).facts;
 if(type==='fixed')facts=reconcile(facts,ms('2026-10-10'),zone,randomUUID).facts;else facts.plans[0]!.revision++;
 const submitted=normalizeEnvelope({commandId:randomUUID(),issuedAtMs:ms('2026-10-09'),kind:type==='fixed'?'SubmitCycleRecord':'SubmitOneTimeResult',payload:{planId,expectedPlanRevision:1,note:'原输入',confirmedToday:'2026-10-09',confirmedEntryKind:'ordinary',...(type==='fixed'?{recordId:randomUUID(),businessOn:'2026-10-09',result:'success'}:{resultId:randomUUID(),outcome:'completed',actualCompletedOn:'2026-10-09'})}});
 const before=JSON.stringify(facts);assert.throws(()=>applyCommand(facts,submitted,ms('2026-10-10'),zone,randomUUID),e=>e instanceof DomainError&&e.code==='DAY_CHANGED');assert.equal(JSON.stringify(facts),before);
});
