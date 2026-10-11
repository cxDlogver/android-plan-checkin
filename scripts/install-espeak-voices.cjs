const {DeviceDriver}=require('./device-driver.cjs'),{createRun}=require('./evidence-run.cjs');
const api=process.argv[2]||'29';
async function main(){const run=createRun(`espeak-tool-voice-install-api${api}`,{api,package:'com.reecedunn.espeak',action:'android.speech.tts.engine.INSTALL_TTS_DATA'},['IP27']);if(!run)return;let d,error;
 try{d=new DeviceDriver(api,run.directory);d.package='com.reecedunn.espeak';d.capabilities={'appium:appActivity':'.eSpeakActivity'};await d.open();run.write('install-data-intent.log',d.adb(['shell','am','start','-W','-a','android.speech.tts.engine.INSTALL_TTS_DATA','-n','com.reecedunn.espeak/.DownloadVoiceData']));await new Promise(r=>setTimeout(r,10000));await d.save('actual-voice-installation');run.write('actual-engine-data-logcat.log',d.adb(['logcat','-d','-t','1500','-s','eSpeakTTS','DownloadVoiceData','SpeechSynthesis']));run.check('actual-install-entry-executed',true,true);}
 catch(e){error=e;}finally{try{await d?.close();}catch{}}
 run.finish(error,['Voice extraction intent executed; actual positive voice count and real synthesis are still required.']);}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
