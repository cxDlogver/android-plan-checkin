const fs=require('node:fs'),{DeviceDriver}=require('./device-driver.cjs'),{createRun}=require('./evidence-run.cjs'),{sha}=require('./p1.cjs');
async function main(){
 const run=createRun('API29-supervised-renderer-recovery-host',{api:29,renderer:'host',noDataWipe:true},[]);if(!run)return;
 const d=new DeviceDriver('29',run.directory);let error;
 try{
  run.write('device.json',d.identity());run.check('native-boot-completed','1',d.adb(['shell','getprop','sys.boot_completed']).trim());
  const renderer=d.adb(['shell','dumpsys','SurfaceFlinger']);run.write('actual-native-renderer.log',renderer);
  run.write('supervised-startup-log.log',fs.readFileSync('.cache/emulator-api29-supervised-host.log','utf8'));
  run.check('actual-hardware-renderer',true,/NVIDIA|GeForce|Intel|AMD|Radeon/i.test(renderer));run.check('not-software-fallback',false,/SwiftShader/i.test(renderer));
  run.write('recovery-scope.json',{scope:'The prior detached API29 process exited after boot. Supervised hardware rendering keeps the same AVD, facts, CPU and RAM; no accepted business action is repeated. Previous failed visual attempts remain immutable.'});
 }catch(e){error=e;}run.finish(error);
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
