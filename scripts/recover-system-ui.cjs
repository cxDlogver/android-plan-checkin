const fs=require('node:fs'),assert=require('node:assert/strict');
const {DeviceDriver}=require('./device-driver.cjs'),{createRun}=require('./evidence-run.cjs'),progress=require('./progress.cjs');
const api=process.argv[2]||'29',device=new DeviceDriver(api,'.cache/system-ui-recovery');
const identity=device.identity();assert.equal(device.adb(['shell','id','-u']).trim(),'0','Only the disposable rooted AOSP AVD is authorized');
const pid=device.adb(['shell','pidof','com.android.systemui']).trim();assert.match(pid,/^\d+$/);
const run=createRun(`system-ui-recovery-api${api}`,{api,pid,reason:'Status bar clock and connectivity icons remained at boot-time state although guest date/window appearance changed.'},['IP04','IP27']);
if(!run)process.exit(0);device.directory=run.directory;device.package='com.xiang.plancheckin';
let error=null;
async function main(){
  run.write('before.json',{identity,pid,guestUtc:device.adb(['shell','date','-u']).trim()});
  device.adb(['shell','kill',pid]);
  let current='';for(let attempt=0;attempt<30;attempt++){try{current=device.adb(['shell','pidof','com.android.systemui']).trim();if(current&&current!==pid)break;}catch{}await new Promise(resolve=>setTimeout(resolve,500));}
  run.check('dedicated-SystemUI-restarted',true,/^\d+$/.test(current)&&current!==pid);
  await device.open();await device.waitSource(source=>source.includes('plan.create'));await device.save('status-after-systemui-recovery');
  run.write('after.json',{pid:current,guestUtc:device.adb(['shell','date','-u']).trim()});
}
main().catch(failure=>{error=failure;console.error(failure.message);}).finally(async()=>{try{await device.close();}catch(failure){error??=failure;}run.finish(error,['Restarts only com.android.systemui on identity-guarded disposable AVD; no app database is changed or feature command repeated.']);});
