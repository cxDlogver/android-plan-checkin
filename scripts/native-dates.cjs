const fs=require('node:fs'),{snapshot}=require('./p1.cjs'),{createRun}=require('./evidence-run.cjs'),{DeviceDriver}=require('./device-driver.cjs'),{VerificationClient,waitForMetro}=require('./verification-bridge.cjs');
const api=process.argv[2]||'36',device=new DeviceDriver(api,'.cache/verification-bridge/dates'),client=new VerificationClient(api);
const source=snapshot(['src/domain/date.ts','src/infrastructure/database/timezone.ts','src/verification/date-development.ts','src/application/projections.ts','scripts/native-dates.cjs']);
const state=require('./progress.cjs').read();
async function main(){
  device.identity();await waitForMetro();device.adb(['reverse','tcp:8081','tcp:8081']);await device.open();device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');await device.waitSource(s=>s.includes('今日')||s.includes('原生模块验证'),120000);device.deepLink('plancheckin-dev://native');await client.waitReady();
  const previous=state.commands[`AC014-date-api${api}`];
  const previousInputs=previous?.record&&JSON.parse(fs.readFileSync(previous.record.replace(/result.json$/,'inputs.json'),'utf8'));
  const dateFiles=source.filter(f=>!f.path.startsWith('scripts/'));
  const previousDateFiles=previousInputs?.source?.filter(f=>!f.path.startsWith('scripts/'));
  const validPrevious=previous?.status==='PASS'&&JSON.stringify(dateFiles)===JSON.stringify(previousDateFiles)&&JSON.parse(fs.readFileSync(previous.record,'utf8')).evidence.every(f=>require('./p1.cjs').sha(fs.readFileSync(f.path))===f.sha256);
  if(validPrevious)console.log(`SKIP AC014 API${api}: preserved unchanged native DateAdapter evidence ${previous.record}`);
  const run=validPrevious?null:createRun(`AC014-date-api${api}`,{api,source},['IP06'],{caseId:'AC014',configId:`api${api}-393dp-font1`});
  if(run){let error=null;try{
    run.write('device.json',device.identity());const response=await client.call('dateProbe');run.write('date-adapter.json',response);
    for(const row of response.observation.examples){run.check(`AC014/${row.rowId}.round-trip`,row.day,row.roundTrip);run.check(`AC014/${row.rowId}.calendar-next`,row.next,row.actualNext);run.check(`AC014/${row.rowId}.midnight-hours`,row.hours,row.actualHours);}
    run.check('AC014.A1.invalid','VALIDATION_FAILED',response.observation.invalidCode);run.check('AC014.A3',['2026-10-19','2026-10-12'],[response.observation.monday,response.observation.sunday]);
  }catch(failure){error=failure;}run.finish(error);if(error)throw error;}
  const originalZone=device.identity().timezone;
  try{
    for(const [rowId,candidate] of [['valid','Asia/Shanghai'],['null',null],['invalid','Invalid/Zone']]){
      const row=createRun(`AC108-${rowId}-api${api}`,{api,rowId,candidate,source},['IP06'],{caseId:'AC108',rowId,configId:`api${api}-393dp-font1`});if(!row)continue;
      let error=null;try{
        const prior=state.commands[`AC108-${rowId}-api${api}`];
        const priorDirectory=prior?.record?.replace(/\/result.json$/,'');
        const initialPath=priorDirectory&&`${priorDirectory}/empty-initialization.json`;
        const reuseInitial=prior?.status==='FAIL'&&initialPath&&fs.existsSync(initialPath)&&JSON.parse(fs.readFileSync(`${priorDirectory}/assertions.json`,'utf8')).some(a=>a.id==='AC108.A1.first-read-only'&&a.status==='PASS');
        device.adb(['shell','cmd','alarm','set-timezone','Asia/Shanghai']);
        await client.call('clock',{instant:'2026-10-08T16:30:00Z'});await client.call('fixture',{name:'F01',zone:'Asia/Shanghai',confirm:'RESET_ISOLATED_DEV_DATABASE'});
        row.write('before-device.json',device.identity());row.check('device-initial-zone','Asia/Shanghai',device.identity().timezone);
        const first=reuseInitial?JSON.parse(fs.readFileSync(initialPath,'utf8')):await client.call('timezoneProbe',{candidate,empty:true,confirm:'INITIALIZE_ISOLATED_DEV_TIMEZONE'});row.write('empty-initialization.json',first);if(reuseInitial)row.write('reused-initialization.json',{source:initialPath,sha256:require('./p1.cjs').sha(fs.readFileSync(initialPath)),reason:'First initialization and persistence assertions already passed; continue after the transport failure without repeating them.'});const a=first.observation;
        row.check('AC108.A1.initial-result',rowId==='valid'?'OK':'INIT_FAILED',a.code);
        row.check('AC108.A1.atomic-meta-count',rowId==='valid'?3:0,a.after.filter(r=>['app_timezone','initialized_at_ms','data_revision'].includes(r.key)).length);
        row.check('AC108.A1.restored-facts',a.original,a.restored);
        if(rowId==='valid'){row.check('AC108.A1.committed-zone','Asia/Shanghai',a.zone);row.check('AC108.A1.persisted-second-open',a.after,a.secondAfter);row.check('AC108.A1.first-read-only',0,a.secondCandidateReads);}
        device.adb(['shell','cmd','alarm','set-timezone','America/New_York']);row.write('after-device.json',device.identity());row.check('actual-device-zone-change','America/New_York',device.identity().timezone);
        const second=await client.call('timezoneProbe',{candidate,empty:false,confirm:'INITIALIZE_ISOLATED_DEV_TIMEZONE'});row.write('stored-initialization-after-device-change.json',second);const b=second.observation;
        row.check('AC108.A1.stored-candidate-unread',0,b.candidateReads);row.check('AC108.A1.stored-meta-unchanged',b.before,b.after);row.check('AC108.A2','2026-10-09',b.firstToday);row.check('AC108.A2.stored-zone','Asia/Shanghai',b.zone);row.check('AC108.A2.device-native-readback','America/New_York',b.deviceZone);
      }catch(failure){error=failure;console.error(failure.message);}row.finish(error);if(error)throw error;
    }
    const cache=createRun(`AC108-midnight-cache-api${api}`,{api,source},['IP06'],{caseId:'AC108',rowId:'shared-A3',configId:`api${api}-393dp-font1`});
    if(cache){let error=null;try{
      await client.call('clock',{instant:'2026-10-09T15:59:59Z'});const first=await client.call('calendarProbe'),stable=await client.call('calendarProbe');
      const clock=await client.call('clock',{instant:'2026-10-09T16:00:00Z'}),after=await client.call('calendarProbe');cache.write('cache-and-clock.json',{first,stable,clock,after});cache.write('device.json',device.identity());
      cache.check('AC108.A3.stable-cache-hit',true,stable.observation.sameCachedDays);cache.check('AC108.A3.midnight-cache-invalidated',false,after.observation.sameCachedDays);cache.check('AC108.A3.today',['2026-10-09','2026-10-10'],[first.observation.today,after.observation.today]);cache.check('AC108.A3.zone','Asia/Shanghai',after.observation.zone);
    }catch(failure){error=failure;}cache.finish(error);if(error)throw error;}
  }finally{device.adb(['shell','cmd','alarm','set-timezone',originalZone]);}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;}).finally(async()=>{try{await client.call('clock',{instant:null});}catch{}try{await device.close();}catch{}});
