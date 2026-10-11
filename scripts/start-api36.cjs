const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict'),{spawn,spawnSync}=require('node:child_process'),{env,toolRoot}=require('./task-env.cjs');
const adb=path.join(toolRoot,'sdk/platform-tools/adb.exe'),devices=spawnSync(adb,['devices'],{env,encoding:'utf8',windowsHide:true});
assert.equal(devices.status,0);if(/^emulator-5562\s+device$/m.test(devices.stdout)){console.log('API36 already online; no emulator start repeated.');process.exit(0);}
assert.ok(os.freemem()>6*1024**3,'At least 6 GiB host memory required before starting the second 4 GiB AVD.');
const config=fs.readFileSync(path.join(toolRoot,'avd/plancheckin_api36.avd/config.ini'),'utf8');assert.match(config,/^hw\.cpu\.ncore\s*=\s*4\s*$/m);assert.match(config,/^hw\.ramSize\s*=\s*4096\s*$/m);
fs.mkdirSync('.cache',{recursive:true});const log=fs.openSync('.cache/emulator-api36.log','a');
const child=spawn(path.join(toolRoot,'sdk/emulator/emulator.exe'),['-avd','plancheckin_api36','-port','5562','-no-window','-no-snapshot','-no-boot-anim'],{env,windowsHide:true,detached:true,stdio:['ignore',log,log]});child.unref();fs.closeSync(log);console.log(JSON.stringify({pid:child.pid,avd:'plancheckin_api36',port:5562,log:'.cache/emulator-api36.log'}));
