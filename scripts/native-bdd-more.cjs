module.exports=({define,client,randomUUID})=>{
for(const row of ['pause','resume','cancel','manual','natural'])define('AC110',row,async t=>{
  const p=await t.create('fixed','2026-10-01',row==='natural'?{endOn:'2026-10-09'}:{});let eventId= randomUUID();
  if(row==='resume'){await t.at('2026-10-08');await t.command('RequestPause',{...await t.ref(p),eventId,confirmedEffectiveOn:'2026-10-09'});eventId=randomUUID();}
  await t.at('2026-10-09');await t.given();
  if(row==='pause'||row==='resume'||row==='cancel'){await t.command(row==='resume'?'RequestResume':'RequestPause',{...await t.ref(p),eventId,confirmedEffectiveOn:'2026-10-10'});if(row==='cancel')await t.command('CancelPendingState',{...await t.ref(p),eventId});}
  if(row==='manual')await t.command('ArchivePlan',{...await t.ref(p),eventId});
  if(row!=='manual')await t.at(row==='natural'?'2026-10-20':'2026-10-10',0);
  const s=await t.snap('after-facts'),detail=await t.query('detail',{planId:p}),right=await t.query('permission',{planId:p,on:s.today});
  t.check(`AC110/${row}.status`,row==='pause'?'paused':row==='manual'||row==='natural'?'archived':'running',detail.status);
  const activeEvents=s.facts.lifecycle_events.filter(e=>e.plan_id===p&&e.cancelled_at_ms===null);
  if(row==='pause')t.check('AC110.A1.stage-end',Date.parse('2026-10-10T00:00:00+08:00'),right.intervals[0].end);
  if(row==='resume')t.check('AC110.A1.new-stage-start',Date.parse('2026-10-10T00:00:00+08:00'),right.intervals.at(-1).start);
  if(row==='cancel'){t.check('AC110.A2.same-stage',1,right.intervals.length);t.check('AC110.A2.open-stage',null,right.intervals[0].end);}
  if(row==='manual'){t.check('AC110.A3.real-instant',t.ms,detail.archive.effective_at_ms);t.check('AC110.A3.empty-today-cancelled',0,(await t.query('calendar',{planId:p,on:'2026-10-09'})).items.length);}
  if(row==='natural')t.check('AC110.A4.original-boundary',Date.parse('2026-10-10T00:00:00+08:00'),detail.archive.effective_at_ms);
  const second=await t.snap('repeated-reconcile');t.check('AC110.idempotent',[s.dataRevision,s.facts.plans.find(x=>x.id===p).revision,activeEvents.length],[second.dataRevision,second.facts.plans.find(x=>x.id===p).revision,second.facts.lifecycle_events.filter(e=>e.plan_id===p&&e.cancelled_at_ms===null).length]);
});
define('AC110','shared-priority-and-rejection',async t=>{
  const p=await t.create('weekly','2026-10-01',{endOn:'2026-10-09'});await t.at('2026-10-09');await t.edit(p,{weeklyTarget:5});const before=await t.given(),oldRevision=before.facts.plans.find(p2=>p2.id===p).revision,eventId=randomUUID();
  await t.command('RequestPause',{...await t.ref(p),eventId,confirmedEffectiveOn:'2026-10-10'});await t.at('2026-10-20');
  const s=await t.snap('reconciled-facts');t.check('AC110.A5.archive-priority','archived',(await t.query('detail',{planId:p})).status);t.check('AC110.A5.cancelled-same-boundary',true,s.facts.lifecycle_events.find(e=>e.id===eventId).cancelled_at_ms!==null);t.check('AC110.A5.cancelled-future-rule',true,s.facts.rule_versions.find(r=>r.plan_id===p&&r.revision===2&&r.kind==='weekly_target').cancelled_at_ms!==null);
  await t.command('EditPlan',{planId:p,expectedPlanRevision:oldRevision,changes:{name:'旧命令'},ruleConfirmations:[]},'PLAN_CHANGED');const after=await t.snap('rejected-user-facts');t.check('AC110.A6.reconcile-survives-user-rejection',s.facts,after.facts);
});
for(const row of ['today','backfill','history','paused','archived','oldstage','future'])define('AC111',row,async t=>{
  const p=await t.create();let r;
  if(row==='history')r=await t.record(p,'2026-10-08','success','历史原文');
  if(row==='paused'||row==='oldstage'){await t.at(row==='paused'?'2026-10-08':'2026-10-04');await t.command('RequestPause',{...await t.ref(p),eventId:randomUUID(),confirmedEffectiveOn:row==='paused'?'2026-10-09':'2026-10-05'});}
  if(row==='oldstage'){await t.at('2026-10-07');await t.command('RequestResume',{...await t.ref(p),eventId:randomUUID(),confirmedEffectiveOn:'2026-10-08'});}
  await t.at('2026-10-09');if(row==='archived')await t.command('ArchivePlan',{...await t.ref(p),eventId:randomUUID()});
  const on=row==='today'?'2026-10-09':row==='future'?'2026-10-10':row==='oldstage'?'2026-10-03':'2026-10-08';
  await t.given();const permission=(await t.query('permission',{planId:p,on,recordId:r})).permission;
  if(row==='today'||row==='backfill'){
    t.check('AC111.permission-before',true,permission.allowed);r=randomUUID();await t.command('SubmitCycleRecord',{...await t.ref(p),recordId:r,businessOn:on,result:'success',note:'初始备注',confirmedToday:'2026-10-09',confirmedEntryKind:row==='today'?'ordinary':'backfill'});
    if(row==='today'){
      await t.command('ModifyCycleRecord',{...await t.ref(p),recordId:r,expectedRecordRevision:1,result:'failure',note:'修正1'});await t.command('ModifyCycleRecord',{...await t.ref(p),recordId:r,expectedRecordRevision:2,result:'skip',note:'修正2'});const s=await t.snap('after-modifications'),record=s.facts.cycle_records.find(x=>x.id===r),original=s.facts.cycle_record_originals.filter(x=>x.record_id===r);
      t.check('AC111.A1.immutable-fields',['2026-10-09','ordinary',3],[record.business_on,record.entry_kind,record.revision]);t.check('AC111.A1.only-first-original',[[r,'success','初始备注']],original.map(x=>[x.record_id,x.original_result,x.original_note]));
    }else{t.check('AC111.A2','READ_ONLY',(await t.query('permission',{planId:p,on,recordId:r})).permission.reason);await t.given();await t.command('ModifyCycleRecord',{...await t.ref(p),recordId:r,expectedRecordRevision:1,result:'failure',note:'不可修改'},'READ_ONLY');await t.unchanged('AC111.A2.no-modification');}
  }else{
    const reason={history:'READ_ONLY',paused:'PAUSED',archived:'ARCHIVED',oldstage:'OLD_STAGE',future:'DATE_INELIGIBLE'}[row];t.check('AC111.A3.reason',reason,permission.reason);
    await t.command(row==='history'?'ModifyCycleRecord':'SubmitCycleRecord',row==='history'?{...await t.ref(p),recordId:r,expectedRecordRevision:1,result:'failure',note:'拒绝'}:{...await t.ref(p),recordId:randomUUID(),businessOn:on,result:'success',note:'拒绝',confirmedToday:'2026-10-09',confirmedEntryKind:row==='future'?'ordinary':'backfill'},reason);await t.unchanged('AC111.A3.unchanged');
    if(row==='oldstage'){await t.command('SubmitCycleRecord',{...await t.ref(p),recordId:randomUUID(),businessOn:'2026-10-08',result:'success',note:'当前阶段允许',confirmedToday:'2026-10-09',confirmedEntryKind:'backfill'});t.check('AC111.A4.current-stage-only',1,(await t.snap()).facts.cycle_records.filter(r2=>r2.plan_id===p).length);}
  }
});
define('AC111','shared-immutable-and-nonselected',async t=>{
  const p=await t.create('fixed','2026-10-01',{weekdayMask:10});await t.at('2026-10-09');await t.given();t.check('AC111.A3.nonselected','DATE_INELIGIBLE',(await t.query('permission',{planId:p,on:'2026-10-09'})).permission.reason);
  await t.command('SubmitCycleRecord',{...await t.ref(p),recordId:randomUUID(),businessOn:'2026-10-09',result:'success',note:'',confirmedToday:'2026-10-09',confirmedEntryKind:'ordinary'},'DATE_INELIGIBLE');
  await t.send(t.envelope('DeleteRecord',{planId:p,recordId:randomUUID()}),'VALIDATION_FAILED');await t.unchanged('AC111.A5.no-record-delete-command');
});
for(const row of ['pending','success','failure','skip'])define('AC113',row,async t=>{
  await client.call('fixture',{name:'F03',zone:'Asia/Shanghai',confirm:'RESET_ISOLATED_DEV_DATABASE'});const before=await t.given(),p=before.facts.plans[0].id;
  if(row!=='pending')await t.record(p,'2026-10-09',row);
  const view=await t.query('detail',{planId:p}),stats=view.statistics;t.check('AC113.A2.fraction',row==='success'?[7,9]:row==='failure'?[6,9]:[6,8],[stats.numerator,stats.denominator]);t.check('AC113.A1.skip',row==='skip'?1:0,stats.skipCount);t.check('AC113.A5.streak',row==='success'?1:0,stats.currentStreak);
});
define('AC113','shared-unknown-zero-stages',async t=>{
  const p=await t.create('fixed','2026-10-07');await t.record(p,'2026-10-07','skip');await t.at('2026-10-08');const zero=(await t.query('detail',{planId:p})).statistics;t.check('AC113.A3',[0,0,null],[zero.numerator,zero.denominator,zero.rate]);await t.at('2026-10-09');const unknown=(await t.query('detail',{planId:p})).statistics;t.check('AC113.A1.unknown',[0,1,1,1,0],[unknown.numerator,unknown.denominator,unknown.skipCount,unknown.pastUnknownCount,unknown.currentStreak]);
  const stages=await t.create('fixed','2026-10-01',{weekdayMask:10});await t.record(stages,'2026-10-01');await t.record(stages,'2026-10-06');await t.at('2026-10-07');t.check('AC113.A5.nonselected-not-breaking',2,(await t.query('detail',{planId:stages})).statistics.currentStreak);
  await t.command('RequestPause',{...await t.ref(stages),eventId:randomUUID(),confirmedEffectiveOn:'2026-10-08'});await t.at('2026-10-09');const paused=(await t.query('detail',{planId:stages})).statistics;t.check('AC113.A5.real-pause-breaks',0,paused.currentStreak);t.check('AC113.A4.paused-gap-excluded',2,paused.denominator);
});
for(const row of ['ontime','late','history','fail','cancel'])define('AC115',row,async t=>{
  const p=await t.create('one_time','2026-10-09',{dueOn:'2026-10-10'});await t.at(row==='ontime'?'2026-10-10':'2026-10-11');const before=await t.given();t.check('AC115.A5.overdue-not-terminal',0,before.facts.one_time_results.length);
  const resultId=randomUUID(),outcome=row==='fail'?'failed':row==='cancel'?'cancelled':'completed',actual=row==='history'?'2026-10-09':row==='ontime'?'2026-10-10':'2026-10-11';
  await t.command('SubmitOneTimeResult',{...await t.ref(p),resultId,outcome,actualCompletedOn:outcome==='completed'?actual:null,note:'终态',confirmedToday:before.today,confirmedEntryKind:row==='history'?'backfill':'ordinary'});const s=await t.snap('terminal-facts'),record=s.facts.one_time_results.find(r=>r.id===resultId),due=s.facts.rule_versions.find(r=>r.id===record.due_rule_version_id);
  t.check('AC115.A2.business-date',actual,record.business_on);t.check('AC115.A2.actual',outcome==='completed'?actual:null,record.actual_completed_on);t.check('AC115.frozen-due','2026-10-10',JSON.parse(due.value_json).dueOn);
  t.check('AC115.A4.before-boundary',row==='history'?'archived':'running',(await t.query('detail',{planId:p})).status);
  if(row!=='history'){await t.command('EditPlan',{...await t.ref(p),changes:{dueOn:'2026-10-15'},ruleConfirmations:[]},'READ_ONLY');await t.at(row==='ontime'?'2026-10-11':'2026-10-12',0);}
  const detail=await t.query('detail',{planId:p});t.check('AC115.A4.archived','archived',detail.status);t.check('AC115.A4.original-instant',row==='history'?Date.parse('2026-10-11T12:00:00+08:00'):Date.parse(`${row==='ontime'?'2026-10-11':'2026-10-12'}T00:00:00+08:00`),detail.archive.effective_at_ms);
  const classification=await t.query('classification',{planId:p,recordId:resultId});t.check('AC115.classification.on-time',row==='ontime'||row==='history',classification.onTime);
  const calendar=await t.query('calendar',{planId:p,on:actual});t.check('AC115.classification',outcome,calendar.items[0].record.outcome);t.check('AC115.calendar-result-replaces-due',1,calendar.items.length);
});
for(const row of ['mixed','weekly0','weeklyskip','once','archive'])define('AC116',row,async t=>{
  let p;
  if(row==='mixed'){
    for(const result of ['success','success','failure','skip',null]){const id=await t.create();if(result)await t.record(id,'2026-10-08',result);}
    await t.at('2026-10-09');
  }else if(row.startsWith('weekly')){p=await t.create('weekly');if(row==='weeklyskip')await t.record(p,'2026-10-08','skip');await t.at('2026-10-09');}
  else {p=await t.create('one_time','2026-10-09',{dueOn:'2026-10-10'});if(row==='once'){await t.at('2026-10-11');await t.command('SubmitOneTimeResult',{...await t.ref(p),resultId:randomUUID(),outcome:'completed',actualCompletedOn:'2026-10-09',note:'',confirmedToday:'2026-10-11',confirmedEntryKind:'backfill'});}else{await t.at('2026-10-09');await t.command('ArchivePlan',{...await t.ref(p),eventId:randomUUID()});}}
  await t.given();const on=row==='once'?'2026-10-09':row==='archive'?'2026-10-10':'2026-10-08',view=await t.query('calendar',{on,planId:p}),day=view.days.find(d=>d.on===on);
  const expected=row==='mixed'?[5,2,'2/5']:row==='weeklyskip'?[1,0,'0/1']:row==='once'?[1,1,'✓']:[0,0,''];t.check(`AC116/${row}.C-T-marker`,expected,[day.total,day.completed,day.label]);
  t.check('AC116.A1.unique-plan-day',view.items.length,new Set(view.items.map(i=>i.key)).size);t.check('AC116.A6.six-weeks',42,view.days.length);
  if(row==='once')t.check('AC116.A3.old-arrangement-gone',0,(await t.query('calendar',{on:'2026-10-10',planId:p})).items.length);
  if(row==='mixed'){const skipped=view.items.find(i=>i.record?.result==='skip');const stats=(await t.query('detail',{planId:skipped.plan.id})).statistics;t.check('AC116.A5.skip-calendar-versus-stat',[1,7],[stats.skipCount,stats.denominator]);}
});
for(const row of ['over','partial','whole','natural','manual'])define('AC114',row,async t=>{
  let p;
  if(row==='over'){p=await t.create('weekly','2026-10-05');for(const on of ['2026-10-05','2026-10-06','2026-10-07','2026-10-08'])await t.record(p,on);await t.at('2026-10-09');await t.given();const s=(await t.query('detail',{planId:p})).statistics;t.check('AC114.A1.over-target',[4,3,1],[s.current.success,s.current.target,s.current.progress]);t.check('AC114.A2.current-excluded',[0,0,0],[s.numerator,s.denominator,s.currentStreak]);return;}
  if(row==='partial'){
    p=await t.create('weekly','2026-09-21');for(const on of ['2026-09-21','2026-09-22','2026-09-23','2026-09-28','2026-09-29','2026-09-30'])await t.record(p,on);
    await t.at('2026-10-06');await t.command('RequestPause',{...await t.ref(p),eventId:randomUUID(),confirmedEffectiveOn:'2026-10-07'});await t.at('2026-10-09');await t.given();const before=(await t.query('detail',{planId:p})).statistics;t.check('AC114.A4.partial-before-end',[2,2,2],[before.numerator,before.denominator,before.currentStreak]);await t.at('2026-10-12',0);const after=(await t.query('detail',{planId:p})).statistics;t.check('AC114.A4.partial-after-end',[2,2,0],[after.numerator,after.denominator,after.currentStreak]);return;
  }
  if(row==='whole'){
    p=await t.create('weekly','2026-09-21');for(const on of ['2026-09-21','2026-09-22','2026-09-23'])await t.record(p,on);await t.at('2026-09-27');await t.command('RequestPause',{...await t.ref(p),eventId:randomUUID(),confirmedEffectiveOn:'2026-09-28'});
    await t.at('2026-10-04');await t.command('RequestResume',{...await t.ref(p),eventId:randomUUID(),confirmedEffectiveOn:'2026-10-05'});await t.at('2026-10-05',0);await t.given();const b=(await t.query('detail',{planId:p})).statistics;t.check('AC114.A4.whole-pause-ended',[1,1,0],[b.numerator,b.denominator,b.currentStreak]);for(const on of ['2026-10-05','2026-10-06','2026-10-07'])await t.record(p,on);await t.at('2026-10-12',0);const c=(await t.query('detail',{planId:p})).statistics;t.check('AC114.A4.next-full-ended',[2,2,1],[c.numerator,c.denominator,c.currentStreak]);return;
  }
  p=await t.create('weekly','2026-10-05',row==='natural'?{endOn:'2026-10-11'}:{});for(const on of ['2026-10-05','2026-10-06','2026-10-07'])await t.record(p,on);
  await t.at('2026-10-11',17);await t.given();if(row==='manual')await t.command('ArchivePlan',{...await t.ref(p),eventId:randomUUID()});await t.at('2026-10-12',0);const after=(await t.query('detail',{planId:p})).statistics;t.check('AC114.A6.boundary-fraction',row==='natural'?[1,1,1]:[0,0,0],[after.numerator,after.denominator,after.currentStreak]);
});
define('AC115','shared-ranges-and-corrections',async t=>{
  const p=await t.create('one_time','2026-10-09',{dueOn:'2026-10-10'});await t.at('2026-10-11');await t.given();
  for(const actual of ['2026-10-08','2026-10-12'])await t.command('SubmitOneTimeResult',{...await t.ref(p),resultId:randomUUID(),outcome:'completed',actualCompletedOn:actual,note:'',confirmedToday:'2026-10-11',confirmedEntryKind:'backfill'},'DATE_INELIGIBLE');
  await t.unchanged('AC115.A1.range-errors-no-write');const resultId=randomUUID();await t.command('SubmitOneTimeResult',{...await t.ref(p),resultId,outcome:'completed',actualCompletedOn:'2026-10-11',note:'原始',confirmedToday:'2026-10-11',confirmedEntryKind:'ordinary'});const original=(await t.snap()).facts.one_time_results.find(r=>r.id===resultId);
  let revision=1;for(const outcome of ['failed','cancelled','completed']){await t.command('ModifyOneTimeResult',{...await t.ref(p),resultId,expectedRecordRevision:revision++,outcome,note:`修正${revision}`});const s=await t.snap(),r=s.facts.one_time_results.find(x=>x.id===resultId);t.check(`AC115.A3.${outcome}`,[original.business_on,original.due_rule_version_id,outcome==='completed'?original.business_on:null],[r.business_on,r.due_rule_version_id,r.actual_completed_on]);t.check('AC115.A3.original-only-once',[[resultId,'completed','原始']],s.facts.one_time_result_originals.filter(x=>x.result_id===resultId).map(x=>[x.result_id,x.original_outcome,x.original_note]));}
});
define('AC116','shared-stable-pagination',async t=>{
  const p=await t.create('fixed','2026-10-01');for(let i=1;i<=8;i++)await t.record(p,`2026-10-0${i}`);await t.at('2026-10-09');await t.given();
  const first=await t.query('history',{planId:p,size:3}),second=await t.query('history',{planId:p,size:3,cursor:first.nextCursor}),third=await t.query('history',{planId:p,size:3,cursor:second.nextCursor});const all=[...first.items,...second.items,...third.items];t.check('AC116.A6.reverse-stable-order',['2026-10-08','2026-10-07','2026-10-06','2026-10-05','2026-10-04','2026-10-03','2026-10-02','2026-10-01'],all.map(r=>r.business_on));t.check('AC116.A6.no-duplicate',8,new Set(all.map(r=>r.id)).size);
  await t.record(p,'2026-10-09');const reset=await t.query('history',{planId:p,size:3,cursor:first.nextCursor});t.check('AC116.A6.revision-resets',[true,'2026-10-09'],[reset.reset,reset.items[0].business_on]);
});
};
