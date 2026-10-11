const {DeviceDriver}=require('./device-driver.cjs'),{createRun}=require('./evidence-run.cjs');
const api=process.argv[2]||'29';
async function main(){const run=createRun(`espeak-tool-data-initialization-api${api}`,{api,package:'com.reecedunn.espeak',scope:'Initialize real bundled eSpeak voice data through its installed app'},['IP27']);if(!run)return;let error,d;
 try{d=new DeviceDriver(api,run.directory);const component=d.adb(['shell','cmd','package','resolve-activity','--brief','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','com.reecedunn.espeak']).trim().split(/\r?\n/).at(-1);run.write('actual-launch-component.log',component);if(!component.includes('com.reecedunn.espeak/'))throw new Error('eSpeak launcher absent');d.package='com.reecedunn.espeak';d.capabilities={'appium:appActivity':component.split('/')[1]};await d.open();await new Promise(r=>setTimeout(r,6000));await d.save('actual-installed-engine-initialization');run.write('engine-logcat.log',d.adb(['logcat','-d','-s','eSpeak','Espeak','SpeechSynthesis','TextToSpeech']));run.check('installed-engine-app-reachable',true,(await d.source()).includes('com.reecedunn.espeak'));}
 catch(e){error=e;}finally{try{await d?.close();}catch{}}
 run.finish(error,['Engine app initialization only; no product or TalkBack acceptance is claimed.']);}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
