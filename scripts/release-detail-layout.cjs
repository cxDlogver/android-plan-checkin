const fs=require('node:fs'),{sha,snapshot}=require('./p1.cjs'),progress=require('./progress.cjs');
const {createRun}=require('./evidence-run.cjs'),{DeviceDriver}=require('./device-driver.cjs');
const api=process.argv[2]||'29',build=progress.read().commands['native-release'],apk=build.artifacts[0];
const run=createRun(`release-detail-layout-api${api}`,{api,apkSha256:apk.sha256,source:snapshot(['src/features/plan-detail.tsx','src/ui/metal.tsx','app/_layout.tsx'])},['IP04','IP27'],{caseId:'AC005',rowId:'default',configId:`api${api}-393dp-font1`,apkSha256:apk.sha256});
if(!run)process.exit(0);
const device=new DeviceDriver(api,run.directory);device.package='com.xiang.plancheckin';let error=null,connectivity;
async function main(){
  run.write('device.json',device.identity());
  connectivity=Object.fromEntries(['airplane_mode_on','wifi_on','mobile_data'].map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()]));
  device.adb(['shell','cmd','connectivity','airplane-mode','enable']);device.adb(['shell','svc','wifi','disable']);device.adb(['shell','svc','data','disable']);
  await device.open();await device.waitSource(source=>source.includes('plan.create'));
  await device.click('tab.plans');const plans=await device.waitSource(source=>source.includes('plan.detail.'));
  const testId=plans.match(/resource-id="(plan\.detail\.[0-9a-f-]{36})"/)?.[1];if(!testId)throw new Error('Existing isolated release seed is required');
  await device.click(testId);await device.waitSource(source=>source.includes('计划详情'));const detail=await device.save('offline-material-detail');
  run.check('existing-detail-rendered',true,detail.includes('计划详情')&&!detail.includes('Unable to load script'));
  const windows=device.adb(['shell','dumpsys','window','windows']);
  run.write('window-appearance.log',windows.split(/\r?\n/).filter(line=>/com\.xiang\.plancheckin|systemUiVisibility|mSystemUiVisibility|LIGHT_STATUS_BAR|mAttrs=|mRequestedVisibilities/.test(line)).join('\n')+'\n');
}
main().catch(async failure=>{error=failure;console.error(failure.message);try{if(device.sessionId)await device.save('failure');}catch{}}).finally(async()=>{
  try{await device.close();}catch(failure){error??=failure;}
  if(connectivity)try{device.adb(['shell','cmd','connectivity','airplane-mode',connectivity.airplane_mode_on==='1'?'enable':'disable']);device.adb(['shell','svc','wifi',connectivity.wifi_on==='1'?'enable':'disable']);device.adb(['shell','svc','data',connectivity.mobile_data==='1'?'enable':'disable']);run.write('connectivity-restored.json',Object.fromEntries(Object.keys(connectivity).map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()])));}catch(failure){error??=failure;}
  run.finish(error,['Only the changed detail-list shadow viewport and system icon appearance are reviewed; no business command is submitted.']);
});
