const fs=require('node:fs'),path=require('node:path'),{sha,snapshot}=require('./p1.cjs'),{runCases}=require('./bdd-ui-session.cjs'),{passed}=require('./run-bdd-matrix.cjs');
const api=process.argv[2]||'36',config=api==='29'?'M3':'M7',key=`AC080-default-${config}`;if(passed(key))process.exit(0);
const saved=require('./progress.cjs').read().commands[key];if(saved?.status!=='FAIL')throw new Error('No bounded failed prefix '+key);
const original=JSON.parse(fs.readFileSync(saved.record)),input=JSON.parse(fs.readFileSync(path.join(path.dirname(saved.record),'inputs.json')));
for(const e of original.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Original filter evidence changed');
for(const file of snapshot(['app','src/features','src/ui','src/state','src/domain','src/application','src/infrastructure/database','src/verification']))if(input.source.find(s=>s.path===file.path)?.sha256!==file.sha256)throw new Error('Product source changed '+file.path);
if(!original.assertions.some(a=>a.id==='AC080.A1.back-keeps-all'&&a.status==='PASS'))throw new Error('Missing accepted back prefix');
const native=JSON.parse(fs.readFileSync(path.join(path.dirname(saved.record),'failure-native-facts.json'))).snapshot;
runCases(api,{AC080:{default:async t=>{
 t.run.assertions.push(...original.assertions.filter(a=>a.status==='PASS'));
 t.run.write('original-back-prefix.json',{report:saved.record,sha256:sha(fs.readFileSync(saved.record)),scope:'Reuse accepted Back/no-filter-change prefix; restore exact original failure facts as Given. Execute only outside dismissal and remaining empty/filter/weekly assertions. Original immediate coordinate tap had no wait for the new modal hierarchy; the continuation waits for the actual modal first.'});
 await t.client.call('factsFixture',{facts:native.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});await t.clock(new Date(native.asOfMs).toISOString());
 await t.nav('/(tabs)/calendar');await t.click('calendar.date.2026-10-08');await t.device.seek('calendar.filter.open');await t.click('calendar.filter.open');await t.device.waitSource(s=>s.includes('calendar.filter.outside')&&s.includes('筛选状态'));
 const before=await t.frame('actual-modal-before-outside-tap'),bounds=before.match(/resource-id="calendar\.filter\.outside"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/);if(!bounds)throw new Error('Actual outside overlay bounds absent');
 const point={x:Number(bounds[1])+1,y:Math.round((Number(bounds[2])+Number(bounds[4]))/2)};t.run.write('actual-outside-hit-point.json',{bounds:bounds[0],point,scope:'Within the real overlay at its left edge, away from centered dialog and system bars.'});
 await t.device.request(t.device.endpoint('execute/sync'),'POST',{script:'mobile: clickGesture',args:[point]});await t.device.waitSource(s=>!s.includes('筛选状态'));await t.textPresent('AC080.A1.outside-keeps-all','全部状态（1）');await t.frame('actual-outside-dismissal');
 await t.click('calendar.filter.open');await t.device.waitSource(s=>s.includes('筛选状态'));await t.click('calendar.filter.completed');await t.device.waitSource(s=>!s.includes('筛选状态'));await t.textPresent('AC080.A2.filtered-empty','该日没有已完成项');await t.device.seeText('可补记的每周计划');await t.textPresent('AC080.A3.independent-weekly','可补记的每周计划');
 const response=await t.client.call('query',{kind:'calendar',on:'2026-10-08'});t.run.write('remaining-calendar-query.json',response);const p=native.facts.plans.find(p=>p.type==='weekly');t.check('AC080.A3.not-in-main',false,response.view.items.some(i=>i.plan.id===p.id));t.check('AC080.A3.eligible',true,response.view.weeklyBackfills.some(x=>x.id===p.id));await t.frame('filtered-empty-and-weekly');
}}},['AC080/default'],config).catch(e=>{console.error(e.stack);process.exitCode=1;});
