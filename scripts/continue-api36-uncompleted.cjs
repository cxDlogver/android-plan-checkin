const {spawn}=require('node:child_process'),fs=require('node:fs'),{env}=require('./task-env.cjs'),{passed}=require('./run-bdd-matrix.cjs'),{DeviceDriver}=require('./device-driver.cjs');
function child(script,args=[],required=true){return new Promise((resolve,reject)=>{const p=spawn(process.execPath,['scripts/'+script,...args],{env,windowsHide:true,stdio:'inherit'});p.on('error',reject);p.on('exit',code=>code&&required?reject(new Error(script+' failed: '+code)):resolve(code));});}
async function display(config){await child('run-bdd-uncompleted.cjs',[config,'display'],false);const command=require('./progress.cjs').read().commands[`AC092-default-${config}`];if(command?.status==='FAIL'){const r=JSON.parse(fs.readFileSync(command.record,'utf8'));if(r.assertions.find(a=>a.status==='FAIL')?.id==='AC092.A2.uniform-six-row-heights')await child('bdd-calendar-clipped-geometry-continuation.cjs',[config],false);}if(!passed(`AC094-default-${config}`))await child('bdd-ui-talkback.cjs',['36',config],false);console.log(config+' machine/a11y scope closed; actual screenshot review remains separate.');}
async function main(){
 const d=new DeviceDriver('36','.cache/api36-continuation');d.identity();d.adb(['shell','wm','density','440']);d.adb(['shell','settings','put','system','font_scale','1']);
 for(const script of ['install-talkback.cjs','install-speech-reader.cjs','install-espeak-engine.cjs','initialize-espeak.cjs','install-espeak-voices.cjs','verify-espeak-voices.cjs'])await child(script,['36']);
 if(!passed('schema-v2-native-api36'))await child('native-migration-v2.cjs',['36']);
 if(!passed('native-schema_too_new-api36'))await child('native-admission.cjs',['36','schema']);
 if(!passed('native-session-observation-api36'))await child('capture-native-session.cjs',['36']);
 const missing=['AC110/shared-effective-cancel-and-history','AC111/shared-forged-immutable-fields','AC113/shared-display-periods','AC114/shared-partial-new-and-resumed','AC116/shared-manual-due-and-list-order','AC041/shared-once-duplicate-and-plan-CAS','AC053/default','AC054/default'].filter(row=>!passed(row.replace('/','-')+'-api36'));
 if(missing.length)await child('native-bdd.cjs',['36',...missing],false);
 await child('run-bdd-uncompleted.cjs',['M7','create','records','lifecycle','calendar','statistics','week-statistics','pages','crash','edit-permission-gaps','once-crossday-form','real-full'],false);
 await display('M7');
 for(const config of ['M5','M6','M8']){await child('run-bdd-matrix.cjs',[config],false);await display(config);}
 await child('update-bdd-coverage.cjs');console.log('API36 pending execution closed. Failures need bounded continuation; raw screenshots need actual review.');
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
