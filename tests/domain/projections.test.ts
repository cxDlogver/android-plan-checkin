import test from 'node:test';
import assert from 'node:assert/strict';
import { Projections } from '../../src/application/projections';
import { DomainError, Snapshot, emptyFacts } from '../../src/domain/model';
import { dayMs } from '../../src/domain/date';
const zone='Asia/Shanghai';
function snapshot(count=121):Snapshot {
  const facts=emptyFacts();
  for(let index=0;index<count;index++){
    const id=`plan-${String(index).padStart(3,'0')}`;
    facts.plans.push({id,type:'fixed',direction:'do',name:'同名计划',description:'',created_at_ms:dayMs('2026-10-01',zone),created_on:'2026-10-01',starts_on:'2026-10-01',revision:1});
    facts.rule_versions.push({id:`rule-${index}`,plan_id:id,kind:'weekday_mask',effective_on:'2026-10-01',revision:1,value_json:'{"weekdayMask":127}',created_at_ms:dayMs('2026-10-01',zone),cancelled_at_ms:null});
  }
  return {facts,today:'2026-10-10',zone,asOfMs:dayMs('2026-10-10',zone)+3600000,dataRevision:0};
}
test('同名同创建时刻计划使用稳定id游标，跨页无遗漏重复且上限100',()=>{
  const q=new Projections(),s=snapshot(),first=q.plans(s,'running'),second=q.plans(s,'running',first.nextCursor),third=q.plans(s,'running',second.nextCursor);
  const all=[...first.items,...second.items,...third.items];assert.equal(all.length,121);assert.equal(new Set(all.map(p=>p.id)).size,121);assert.equal(third.nextCursor,null);assert.equal(q.plans(s,'running',null,999).items.length,100);
});
test('业务日、时区、revision、筛选变化使游标重置，永久删除不读旧缓存',()=>{
  const q=new Projections(),s=snapshot(),first=q.plans(s,'running');
  for(const changed of [{...s,today:'2026-10-11'},{...s,zone:'America/New_York'},{...s,dataRevision:1}]){const next=q.plans(changed,'running',first.nextCursor);assert.equal(next.reset,true);assert.equal(next.items[0]?.id,'plan-000');}
  assert.equal(q.plans(s,'paused',first.nextCursor).reset,true);
  q.detail(s,'plan-000');const removed={...s,dataRevision:1,facts:{...s.facts,plans:s.facts.plans.slice(1)}};
  assert.throws(()=>q.detail(removed,'plan-000'),e=>e instanceof DomainError&&e.code==='TARGET_REMOVED');
});
test('月历完整集合用于分子分母；今日隐藏标记，42格一次投影',()=>{
  const q=new Projections(),s=snapshot(3);s.facts.cycle_records.push({id:'record',plan_id:'plan-000',business_on:'2026-10-09',result:'success',note:'',entry_kind:'ordinary',submitted_at_ms:dayMs('2026-10-09',zone),modified_at_ms:null,revision:1});
  const calendar=q.calendar(s,'2026-10','2026-10-09');assert.equal(calendar.days.length,42);assert.equal(calendar.items.length,3);assert.equal(calendar.days.find(d=>d.on==='2026-10-09')?.label,'1/3');assert.equal(calendar.days.find(d=>d.on===s.today)?.label,'');
  assert.equal(q.calendar(s,'2026-10','2026-10-10').days,calendar.days);
});
test('历史倒序分页和版本变化重置；记录权限/原值均来自同一快照',()=>{
  const q=new Projections(),s=snapshot(1);
  for(let index=1;index<=9;index++)s.facts.cycle_records.push({id:`r${index}`,plan_id:'plan-000',business_on:`2026-10-0${index}`,result:'success',note:'',entry_kind:'ordinary',submitted_at_ms:dayMs('2026-10-10',zone),modified_at_ms:null,revision:1});
  const first=q.history(s,'plan-000',null,4),second=q.history(s,'plan-000',first.nextCursor,4);assert.deepEqual(first.items.map(r=>r.business_on),['2026-10-09','2026-10-08','2026-10-07','2026-10-06']);assert.equal(second.items[0]?.business_on,'2026-10-05');assert.equal(q.history({...s,dataRevision:1},'plan-000',first.nextCursor,4).reset,true);assert.equal(q.record(s,'plan-000','r9').permission.reason,'READ_ONLY');assert.equal(q.settings(s,null,null).nativeVersion,'不可用');
});
