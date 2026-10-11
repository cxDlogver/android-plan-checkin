const fs=require('node:fs'),assert=require('node:assert/strict');
const {sha,snapshot}=require('./p1.cjs'),progress=require('./progress.cjs');
const {createRun}=require('./evidence-run.cjs'),{DeviceDriver}=require('./device-driver.cjs');
const api=process.argv[2]||'29',state=progress.read(),build=state.commands['native-release'];
const resume=process.argv.includes('resume'),previous=state.commands[`release-material-api${api}`];
assert.equal(build.status,'PASS');const apk=build.artifacts[0];assert.equal(sha(fs.readFileSync(apk.path)),apk.sha256);
const run=createRun(`release-material-api${api}`,{api,apk,source:snapshot(['src/ui/metal.tsx','app/_layout.tsx','app/(tabs)/_layout.tsx'])},['IP04','IP28'],{caseId:'AC005',rowId:'default',configId:`api${api}-393dp-font1`,apkSha256:apk.sha256,buildRecord:build.record});
if(!run)process.exit(0);
const device=new DeviceDriver(api,run.directory);device.package='com.xiang.plancheckin';
let connectivity,error=null;
async function main(){
  run.write('device.json',device.identity());
  let reused;
  if(resume){assert.equal(previous.status,'FAIL');assert.equal(previous.inputSha256,sha(JSON.stringify({api,apk,source:snapshot(['src/ui/metal.tsx','app/_layout.tsx','app/(tabs)/_layout.tsx'])})));reused=JSON.parse(fs.readFileSync(previous.record,'utf8'));assert.ok(reused.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256));run.assertions.push(...reused.assertions.filter(assertion=>assertion.status==='PASS'));run.write('reused-evidence.json',{record:previous.record,evidence:reused.evidence});}
  let available=false;try{await fetch('http://127.0.0.1:8081/status',{signal:AbortSignal.timeout(1500)});available=true;}catch{}
  if(!resume)run.check('AC005.A3.no-Metro',false,available);else assert.equal(available,false);
  run.write('previous-package.log',device.adb(['shell','pm','path',device.package]));
  connectivity=Object.fromEntries(['airplane_mode_on','wifi_on','mobile_data'].map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()]));run.write('connectivity-before.json',connectivity);
  device.adb(['shell','cmd','connectivity','airplane-mode','enable']);device.adb(['shell','svc','wifi','disable']);device.adb(['shell','svc','data','disable']);
  run.write('connectivity-offline.json',Object.fromEntries(Object.keys(connectivity).map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()])));
  if(!resume)run.write('install.log',device.adb(['install','-r',apk.path]));
  await device.open();await device.waitSource(source=>source.includes('今日')&&source.includes('plan.create'));
  if(!resume){
  const today=await device.save('offline-material-today');
  run.check('AC005.A3.embedded-Chinese',true,today.includes('今日')&&today.includes('计划')&&today.includes('日历'));
  run.check('AC005.A3.no-launcher-or-load-error',false,/development servers|Loading from Metro|Unable to load script|Error loading font/i.test(today));
  await device.click('tab.plans');await device.waitSource(source=>source.includes('plan.create'));
  const plans=await device.save('offline-material-plans');
  const seeded=state.commands[`release-offline-${api}`].seededName;
  run.check('same-certificate-replacement-retains-existing-data',true,plans.includes(seeded));
  }
  await device.click('tab.calendar');await device.waitSource(source=>source.includes('calendar.month.previous'));
  await device.save('offline-material-calendar');
  await device.click('tab.today');await device.waitSource(source=>source.includes('今日')&&source.includes('plan.create'));
  await device.text('设置');await device.waitSource(source=>source.includes('本机设置'));await device.save('offline-material-settings');
  await device.back();
  await device.click('tab.today');await device.click('plan.create');await device.waitSource(source=>source.includes('plan.name'));
  await device.save('offline-material-input');
  await device.back();
}
main().catch(async failure=>{error=failure;console.error(failure.message);try{if(device.sessionId)await device.save('failure');}catch{}}).finally(async()=>{
  try{await device.close();}catch(failure){error??=failure;}
  if(connectivity)try{device.adb(['shell','cmd','connectivity','airplane-mode',connectivity.airplane_mode_on==='1'?'enable':'disable']);device.adb(['shell','svc','wifi',connectivity.wifi_on==='1'?'enable':'disable']);device.adb(['shell','svc','data',connectivity.mobile_data==='1'?'enable':'disable']);run.write('connectivity-restored.json',Object.fromEntries(Object.keys(connectivity).map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()])));}catch(failure){error??=failure;}
  run.finish(error,['Only material gradients/shadows and final APK resource/navigation rendering are newly checked; prior passing create/record/cancel flows are reused.','Replacement keeps versionCode=1 and is not the planned version/schema upgrade acceptance.','No new business write is submitted; the existing offline seed is read back.']);
});
