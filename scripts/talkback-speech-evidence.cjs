const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process'),{toolRoot,env}=require('./task-env.cjs');
const PACKAGE='com.xiang.verification.reader',SERVICE='com.android.talkback/com.google.android.marvin.talkback.TalkBackService';
function binary(d,args){return execFileSync(path.join(toolRoot,'sdk/platform-tools/adb.exe'),['-s',d.serial,...args],{env,timeout:30000,windowsHide:true,maxBuffer:32*1024*1024});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function files(d){try{return d.adb(['shell','run-as',PACKAGE,'ls','files']).trim().split(/\s+/).filter(f=>/^\d+-\d+\.json$/.test(f));}catch{return [];}}
function read(d,file){return JSON.parse(binary(d,['exec-out','run-as',PACKAGE,'cat',`files/${file}`]).toString('utf8'));}
async function setup(d,run){
 const saved={};for(const key of ['enabled_accessibility_services','accessibility_enabled','tts_default_synth','tts_default_locale','tts_default_rate','tts_default_pitch'])saved[key]=d.adb(['shell','settings','get','secure',key]).trim();run.write('original-emulator-accessibility-settings.json',saved);
 const restore=()=>{d.adb(['shell','settings','put','secure','enabled_accessibility_services',saved.enabled_accessibility_services==='null'?'':saved.enabled_accessibility_services]);for(const [key,value]of Object.entries(saved)){if(key==='enabled_accessibility_services')continue;d.adb(['shell','settings',value==='null'?'delete':'put','secure',key,...(value==='null'?[]:[value])]);}};
 try{
  d.adb(['shell','settings','put','secure','enabled_accessibility_services','']);d.adb(['shell','am','force-stop','com.android.talkback']);
  const prefs='<?xml version="1.0" encoding="utf-8"?><map><boolean name="first_time_user" value="false"/><boolean name="has_training_exit" value="true"/><boolean name="has_onboarding_exit" value="true"/><boolean name="pref_update_welcome_16_2_shown_key" value="true"/><string name="pref_log_level">2</string></map>';
  const local=path.resolve(run.directory,'talkback-configuration-Given.xml'),remote=`/data/local/tmp/plancheckin-talkback-prefs-api${d.api}.xml`;fs.writeFileSync(local,prefs);d.adb(['push',local,remote]);const dir='/data/user_de/0/com.android.talkback/shared_prefs';d.adb(['shell','run-as','com.android.talkback','mkdir','-p',dir]);d.adb(['shell','run-as','com.android.talkback','cp',remote,`${dir}/com.android.talkback_preferences.xml`]);d.adb(['shell','rm','--',remote]);
  for(const [key,value]of Object.entries({tts_default_synth:PACKAGE,tts_default_locale:`${PACKAGE}:zh-CN`,tts_default_rate:'100',tts_default_pitch:'100',accessibility_enabled:'1'}))d.adb(['shell','settings','put','secure',key,value]);
  d.adb(['shell','settings','put','secure','enabled_accessibility_services',SERVICE]);await sleep(4000);run.write('actual-enabled-service.log',d.adb(['shell','dumpsys','accessibility']));run.write('actual-TTS-service.log',d.adb(['shell','dumpsys','texttospeech']));run.check('TalkBack.actual-service-enabled',true,d.adb(['shell','settings','get','secure','enabled_accessibility_services']).includes(SERVICE));return restore;
 }catch(e){restore();throw e;}
}
async function captureSpeech(d,run,name,before,expected,timeout=40000){
 const deadline=Date.now()+timeout;let observed=[];
 do{observed=files(d).filter(f=>!before.has(f)).map(f=>({file:f,meta:read(d,f)}));const complete=observed.filter(o=>!o.meta.stopped&&o.meta.offeredBytes===o.meta.pcmBytes&&o.meta.pcmBytes>0&&o.meta.callerPackages.includes('com.android.talkback'));
  const match=complete.find(o=>o.meta.text.includes(expected));if(match){for(const {file,meta}of complete){run.write(`${name}-${file}`,meta);fs.writeFileSync(path.join(run.directory,`${name}-${file.replace('.json','.wav')}`),binary(d,['exec-out','run-as',PACKAGE,'cat',`files/${file.replace('.json','.wav')}`]));}run.write(`${name}-spoken-observations.json`,complete.map(o=>o.meta));run.check(`${name}.actual-TalkBack-PCM`,true,!!match);return match.meta;}
  await sleep(500);
 }while(Date.now()<deadline);run.write(`${name}-speech-timeout.json`,observed);throw new Error(`TalkBack did not deliver complete PCM for ${expected}`);
}
async function focus(d,run,name,bounds,expected){const before=new Set(files(d)),match=bounds.match(/\[(\d+),(\d+)\]\[(\d+),(\d+)\]/);if(!match)throw new Error('Missing actual focus target bounds');const [,l,t,r,b]=match.map(Number),x=Math.round((l+r)/2),y=Math.round((t+b)/2);run.write(`${name}-actual-touch.json`,{at:new Date().toISOString(),x,y,bounds,action:'single native touch exploration tap; actual TalkBack focus and speech'});d.adb(['shell','input','tap',String(x),String(y)]);await captureSpeech(d,run,name,before,expected);await d.save(`${name}-focused`);return {x,y};}
module.exports={setup,files,read,captureSpeech,focus,sleep,SERVICE,PACKAGE,binary};
