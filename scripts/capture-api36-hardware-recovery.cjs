const fs=require('node:fs'),{DeviceDriver}=require('./device-driver.cjs'),{createRun}=require('./evidence-run.cjs'),{sha}=require('./p1.cjs');
async function main(){
 const run=createRun('API36-supervised-renderer-recovery-host',{api:36,renderer:'host',noDataWipe:true},[]);if(!run)return;
 const d=new DeviceDriver('36',run.directory);let error;
 try{
  run.write('device.json',d.identity());run.check('native-boot-completed','1',d.adb(['shell','getprop','sys.boot_completed']).trim());
  const renderer=d.adb(['shell','dumpsys','SurfaceFlinger']);run.write('actual-native-renderer.log',renderer);
  run.write('supervised-startup-log.log',fs.readFileSync('.cache/emulator-api36-supervised-host.log','utf8'));
  run.check('actual-hardware-renderer',true,/NVIDIA|GeForce|Intel|AMD|Radeon/i.test(renderer));run.check('not-software-fallback',false,/SwiftShader/i.test(renderer));
  run.write('recovery-scope.json',{previousStart:'resource/acceptance/runs/2026-10-11T19-26-08-348Z/API36-single-AVD-start/result.json',originalFailedUI:'resource/acceptance/runs/2026-10-11T19-37-47-997Z/AC024-success-M7/result.json',sourceSHA256:sha(fs.readFileSync('scripts/run-api36.cjs')),scope:'The supervised direct SwiftShader process exited with 3221225477 (0xC0000005) during a scroll. The prior swangle request also selected direct SwiftShader according to its startup log and crashed; it did not prove ANGLE. This recovery records the actually selected hardware renderer. Same AVD/data/CPU/RAM. Completed native observations are retained. No out-of-memory claim or successful UI recovery claim is made by boot-only evidence.',officialOption:'https://developer.android.com/studio/run/emulator-acceleration'});
 }catch(e){error=e;}run.finish(error);
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
