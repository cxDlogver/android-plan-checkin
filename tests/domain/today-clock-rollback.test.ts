import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {applyCommand,normalizeEnvelope} from '../../src/domain/commands';
import {dayMs} from '../../src/domain/date';
import {emptyFacts,setMeta,Snapshot} from '../../src/domain/model';
import {todaySections} from '../../src/domain/rules';
test('AC083 clock rollback before creation excludes future-created plans without sorting undefined due rules',()=>{
 const zone='Asia/Shanghai',on='2026-10-09',now=dayMs(on,zone)+12*3600000;let facts=emptyFacts();setMeta(facts,'app_timezone',zone);setMeta(facts,'data_revision','0');
 for(const type of ['fixed','weekly','one_time','one_time'] as const){facts=applyCommand(facts,normalizeEnvelope({commandId:randomUUID(),issuedAtMs:now,kind:'CreatePlan',payload:{planId:randomUUID(),type,name:'回拨回归',description:'',direction:'do',...(type==='one_time'?{dueOn:on}:{startsOn:on,endOn:null,...(type==='fixed'?{weekdayMask:127}:{weeklyTarget:3})})}}),now,zone,randomUUID).facts;}
 const snapshot:Snapshot={facts,zone,today:'2026-10-08',asOfMs:dayMs('2026-10-08',zone)+12*3600000,dataRevision:4},before=JSON.stringify(facts);assert.deepEqual(todaySections(snapshot),{fixed:[],weekly:[],once:[],recorded:[]});assert.equal(JSON.stringify(facts),before);assert.equal(todaySections({...snapshot,today:on,asOfMs:now}).once.length,2);
});
