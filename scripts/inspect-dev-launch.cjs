const fs=require('node:fs');
const {DeviceDriver}=require('./device-driver.cjs');
async function main(){const api=process.argv[2]||'29',device=new DeviceDriver(api,'.cache/dev-launch');
  const identity=device.identity();let pid='';try{pid=device.adb(['shell','pidof',device.package]).trim();}catch{}
  let metro;try{metro=await (await fetch('http://127.0.0.1:8081/status',{signal:AbortSignal.timeout(5000)})).text();}catch(error){metro=error.message;}
  const activity=device.adb(['shell','dumpsys','activity','activities']).split(/\r?\n/).filter(line=>/mResumedActivity|topResumedActivity|mFocusedActivity/.test(line));
  const report={identity,pid,metro,activity,reverse:device.adb(['reverse','--list']).trim()};
  fs.writeFileSync(`.cache/dev-launch/api${api}.json`,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
  if(pid){const log=device.adb(['logcat','-d',`--pid=${pid}`,'ReactNative:V','ReactNativeJS:V','AndroidRuntime:E','DevLauncher:V','*:S']);fs.writeFileSync(`.cache/dev-launch/api${api}.log`,log);console.log(log.slice(-6000));}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
