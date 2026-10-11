import { buildFixture } from './fixtures';
import { dayMs } from '../domain/date';
export function migrationV2Given(){
  const today='2026-10-09',zone='Asia/Shanghai',facts=buildFixture('F02',today,zone),other=buildFixture('F01',today,zone),at=dayMs(today,zone)+3600000;
  for(const table of ['plans','rule_versions'] as const)(facts[table] as object[]).push(...other[table]);
  const cycle=facts.cycle_records[0]!;
  facts.cycle_record_originals.push({record_id:cycle.id,original_result:cycle.result,original_note:cycle.note});
  cycle.result='failure';cycle.note='更正后周期备注';cycle.modified_at_ms=at;cycle.revision=2;
  const once=facts.plans.find(p=>p.type==='one_time')!,due=facts.rule_versions.find(r=>r.plan_id===once.id&&r.kind==='due_on')!;
  const id='22222222-2222-4222-8222-222222222222';
  facts.one_time_results.push({id,plan_id:once.id,business_on:today,outcome:'completed',actual_completed_on:today,due_rule_version_id:due.id,note:'更正后一次性备注',entry_kind:'ordinary',submitted_at_ms:at,modified_at_ms:at+1000,revision:2});
  facts.one_time_result_originals.push({result_id:id,original_outcome:'failed',original_note:'首次失败备注'});
  const weekly=facts.plans.find(p=>p.type==='weekly')!;
  facts.rule_versions.push({id:'33333333-3333-4333-8333-333333333333',plan_id:weekly.id,kind:'weekly_target',effective_on:'2026-10-12',revision:2,value_json:'{"weeklyTarget":4}',created_at_ms:at,cancelled_at_ms:null});
  facts.lifecycle_events.push({id:'44444444-4444-4444-8444-444444444444',plan_id:weekly.id,kind:'pause',source_key:'migration-v2-future-pause',effective_on:'2026-10-10',effective_at_ms:dayMs('2026-10-10',zone),reason:'user',requested_at_ms:at,cancelled_at_ms:null});
  return facts;
}
