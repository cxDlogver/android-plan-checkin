import { test } from 'node:test';
import assert from 'node:assert/strict';
import { addDays, businessToday, date, dayMs, nextMonday } from '../../src/domain/date';
import { DomainError, Snapshot, emptyFacts } from '../../src/domain/model';
import { Projections } from '../../src/application/projections';

const examples=[['spring','America/New_York','2026-03-08','2026-03-09',23],['fall','America/New_York','2026-11-01','2026-11-02',25],['leap','Asia/Shanghai','2028-02-28','2028-02-29',24],['year','Asia/Shanghai','2026-12-31','2027-01-01',24]] as const;
for(const [rowId,zone,input,expected,hours] of examples)test(`AC014/${rowId}: round trip and calendar successor`,()=>{
  assert.equal(date(input,zone).toISODate(),input);
  assert.equal(addDays(input,1,zone),expected);
  assert.equal((dayMs(expected,zone)-dayMs(input,zone))/3600000,hours);
});
test('AC014/A1-A3 invalid date and strict Sunday successor',()=>{
  assert.throws(()=>date('2026-02-30'),error=>error instanceof DomainError&&error.code==='VALIDATION_FAILED');
  assert.equal(nextMonday('2026-10-11','Asia/Shanghai'),'2026-10-12');
});
test('AC108/A2-A3 fixed zone and calendar cache at business midnight',()=>{
  const zone='Asia/Shanghai',instant=Date.parse('2026-10-08T16:30:00Z');
  assert.equal(businessToday(instant,zone),'2026-10-09');
  const before:Snapshot={facts:emptyFacts(),today:'2026-10-09',zone,asOfMs:Date.parse('2026-10-09T15:59:59Z'),dataRevision:0};
  const projections=new Projections(),first=projections.calendar(before,'2026-10','2026-10-09');
  assert.equal(projections.calendar(before,'2026-10','2026-10-09').days,first.days);
  const after={...before,asOfMs:Date.parse('2026-10-09T16:00:00Z'),today:'2026-10-10'};
  assert.notEqual(projections.calendar(after,'2026-10','2026-10-09').days,first.days);
  assert.notEqual(projections.calendar({...after,zone:'America/New_York'},'2026-10','2026-10-09').days,projections.calendar(after,'2026-10','2026-10-09').days);
});
