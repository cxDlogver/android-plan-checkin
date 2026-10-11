import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { applyCommand, normalizeEnvelope, reconcile } from '../../src/domain/commands';
import { dayMs } from '../../src/domain/date';
import { fixedStatistics, isOnTime, pendingRules, permission, ruleValue, status, weeklyStatistics } from '../../src/domain/rules';
import { CommandKind, Facts, Plan, Snapshot, emptyFacts, metaValue, setMeta } from '../../src/domain/model';
const zone='Asia/Shanghai';
const ms=(on:string,hour=12)=>dayMs(on,zone)+hour*3600000;
function initial(){const facts=emptyFacts();setMeta(facts,'app_timezone',zone);setMeta(facts,'data_revision','0');return facts;}
function execute(facts:Facts,kind:CommandKind,payload:Record<string,unknown>,on='2026-10-09',hour=12){return applyCommand(facts,normalizeEnvelope({commandId:randomUUID(),issuedAtMs:ms(on,hour),kind,payload}),ms(on,hour),zone,randomUUID).facts;}
function create(type:Plan['type'],on='2026-10-01',options:Record<string,unknown>={}){const planId=randomUUID();const facts=execute(initial(),'CreatePlan',{planId,type,name:'BDD',description:'',direction:'do',...(type==='one_time'?{dueOn:'2026-10-10'}:{startsOn:on,endOn:null,...(type==='fixed'?{weekdayMask:127}:{weeklyTarget:3})}),...options},on);return {facts,planId};}
const ref=(facts:Facts,planId:string)=>({planId,expectedPlanRevision:facts.plans.find(p=>p.id===planId)!.revision});
const snap=(facts:Facts,on='2026-10-09',hour=12):Snapshot=>({facts,today:on,zone,asOfMs:ms(on,hour),dataRevision:Number(metaValue(facts,'data_revision'))});
const record=(facts:Facts,planId:string,on:string,result='success')=>execute(facts,'SubmitCycleRecord',{...ref(facts,planId),recordId:randomUUID(),businessOn:on,result,note:'',confirmedToday:on,confirmedEntryKind:'ordinary'},on);
test('AC109 weekly replacement 3 to 5 to 4 keeps only final pending and never reuses revision',()=>{
  let {facts,planId}=create('weekly');
  for(const weeklyTarget of [5,4])facts=execute(facts,'EditPlan',{...ref(facts,planId),changes:{weeklyTarget},ruleConfirmations:[{field:'weekly_target',confirmedEffectiveOn:'2026-10-12'}]});
  const rules=facts.rule_versions.filter(r=>r.plan_id===planId&&r.kind==='weekly_target');assert.deepEqual(rules.map(r=>r.revision),[1,2,3]);assert.notEqual(rules[1]!.cancelled_at_ms,null);assert.equal(rules[2]!.cancelled_at_ms,null);assert.equal(ruleValue(facts,planId,'weekly_target','2026-10-09'),3);assert.equal(ruleValue(facts,planId,'weekly_target','2026-10-12'),4);
  facts=execute(facts,'EditPlan',{...ref(facts,planId),changes:{weeklyTarget:3},ruleConfirmations:[{field:'weekly_target',confirmedEffectiveOn:'2026-10-12'}]});assert.equal(pendingRules(facts,planId,'2026-10-09').length,0);assert.equal(ruleValue(facts,planId,'weekly_target','2026-10-12'),3);
});
test('AC113 missing fixed skip fraction and failure denominator from 6 of 8 history',()=>{
  let {facts,planId}=create('fixed');for(let i=1;i<=8;i++)facts=record(facts,planId,`2026-10-0${i}`,i<=6?'success':'failure');
  const skipped=record(facts,planId,'2026-10-09','skip'),stats=fixedStatistics(snap(skipped),skipped.plans[0]!);assert.deepEqual([stats.numerator,stats.denominator,stats.skipCount,stats.currentStreak],[6,8,1,0]);
  const failed=record(facts,planId,'2026-10-09','failure');assert.equal(fixedStatistics(snap(failed),failed.plans[0]!).denominator,9);
});
test('AC114 two complete weeks survive an unfinished partial week then reset at its end',()=>{
  let {facts,planId}=create('weekly','2026-09-21');for(const on of ['2026-09-21','2026-09-22','2026-09-23','2026-09-28','2026-09-29','2026-09-30'])facts=record(facts,planId,on);
  facts=execute(facts,'RequestPause',{...ref(facts,planId),eventId:randomUUID(),confirmedEffectiveOn:'2026-10-07'},'2026-10-06');
  const before=weeklyStatistics(snap(facts),facts.plans[0]!);assert.deepEqual([before.numerator,before.denominator,before.currentStreak],[2,2,2]);const after=weeklyStatistics(snap(facts,'2026-10-12',0),facts.plans[0]!);assert.deepEqual([after.numerator,after.denominator,after.currentStreak],[2,2,0]);
});
test('AC114 natural Sunday boundary counts a full week; over-target preserves actual count',()=>{
  let {facts,planId}=create('weekly','2026-10-05',{endOn:'2026-10-11'});for(const on of ['2026-10-05','2026-10-06','2026-10-07','2026-10-08'])facts=record(facts,planId,on);
  const current=weeklyStatistics(snap(facts),facts.plans[0]!);assert.deepEqual([current.current!.success,current.current!.target,current.current!.progress],[4,3,1]);
  facts=reconcile(facts,ms('2026-10-12',0),zone,randomUUID).facts;const after=weeklyStatistics(snap(facts,'2026-10-12',0),facts.plans[0]!);assert.deepEqual([after.numerator,after.denominator,after.currentStreak],[1,1,1]);
});
for(const [row,on,outcome,actual,expected] of [['ontime','2026-10-10','completed','2026-10-10',true],['late','2026-10-11','completed','2026-10-11',false],['history','2026-10-11','completed','2026-10-09',true],['fail','2026-10-11','failed',null,false],['cancel','2026-10-11','cancelled',null,false]] as const)test(`AC115/${row} frozen cutoff classification`,()=>{
  let {facts,planId}=create('one_time','2026-10-09');facts=execute(facts,'SubmitOneTimeResult',{...ref(facts,planId),resultId:randomUUID(),outcome,actualCompletedOn:actual,note:'',confirmedToday:on,confirmedEntryKind:row==='history'?'backfill':'ordinary'},on);const result=facts.one_time_results[0]!,due=facts.rule_versions.find(r=>r.id===result.due_rule_version_id)!;assert.equal(isOnTime(result,due),expected);assert.equal(result.business_on,actual||on);assert.equal(result.actual_completed_on,actual);
});
