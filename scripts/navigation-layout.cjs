const fs=require('node:fs'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const {DeviceDriver,decode}=require('./device-driver.cjs'),progress=require('./progress.cjs');
const api=process.argv[2]||'36',replace=process.argv.slice(3).includes('replace'),resume=process.argv.slice(3).includes('resume'),state=progress.read(),build=state.commands['native-release'];assert.equal(build.status,'PASS');const apk=build.artifacts[0];
const sha=value=>createHash('sha256').update(value).digest('hex');assert.equal(sha(fs.readFileSync(apk.path)),apk.sha256);
const previous=state.commands[`navigation-layout-${api}`];if(previous?.status==='PASS'&&previous.apkSha256===apk.sha256&&previous.evidence.every(item=>fs.existsSync(item.path)&&sha(fs.readFileSync(item.path))===item.sha256)){console.log(`SKIP: ${previous.record}`);process.exit(0);}
const startedAt=new Date().toISOString(),directory=`resource/acceptance/runs/${startedAt.replace(/[:.]/g,'-')}/navigation-layout-api${api}`,device=new DeviceDriver(api,directory);device.package='com.xiang.plancheckin';
const prior=resume&&previous?.record?JSON.parse(fs.readFileSync(previous.record,'utf8')):null,reusedEvidence=[];
if(prior){assert.equal(prior.apkSha256,apk.sha256);assert.ok(prior.evidence.every(item=>fs.existsSync(item.path)&&sha(fs.readFileSync(item.path))===item.sha256));reusedEvidence.push(...prior.evidence,{path:previous.record,sha256:sha(fs.readFileSync(previous.record))});}
const assertions=[],store=(name,value)=>fs.writeFileSync(`${directory}/${name}`,typeof value==='string'?value:JSON.stringify(value,null,2)+'\n');
if(prior)assertions.push(...prior.assertions.filter(item=>item.status==='PASS').map(item=>({...item,reusedFrom:previous.record})));
function check(id,expected,actual){const status=JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL';assertions.push({id,expected,actual,status});store('assertions.json',assertions);console.log(`${status} ${id}`);assert.equal(status,'PASS',id);}
function nodes(source){return [...source.matchAll(/<android\.widget\.TextView\b[^>]*>/g)].map(match=>Object.fromEntries([...match[0].matchAll(/([\w-]+)="([^"]*)"/g)].map(attribute=>[attribute[1],decode(attribute[2])])));}
function rect(bounds){const values=bounds.match(/\d+/g)?.map(Number);assert.equal(values?.length,4);return {left:values[0],top:values[1],right:values[2],bottom:values[3]};}
let originalScale,originalConnectivity;
async function main(){
  const identity=device.identity();store('device.json',identity);originalScale=identity.fontScale;
  if(replace){
    originalConnectivity=Object.fromEntries(['airplane_mode_on','wifi_on','mobile_data'].map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()]));store('connectivity-before.json',originalConnectivity);
    device.adb(['shell','cmd','connectivity','airplane-mode','enable']);device.adb(['shell','svc','wifi','disable']);device.adb(['shell','svc','data','disable']);store('connectivity-offline.json',Object.fromEntries(Object.keys(originalConnectivity).map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()])));
    check('replacement-layout.airplane-enabled','1',device.adb(['shell','settings','get','global','airplane_mode_on']).trim());let metroAvailable=false;try{await fetch('http://127.0.0.1:8081/status',{signal:AbortSignal.timeout(1500)});metroAvailable=true;}catch{}check('replacement-layout.no-metro',false,metroAvailable);
    store('install-replace.log',device.adb(['install','-r',apk.path]));await device.open();await device.waitSource(source=>source.includes('plan.create'));await device.click('tab.plans');const expectedName=state.commands[`release-offline-${api}`]?.seededName;assert.ok(expectedName,'An earlier persisted test plan is required.');const ui=await device.waitSource(source=>source.includes(expectedName));await device.save('existing-data-after-replacement');check('same-certificate-replacement-preserves-data',true,ui.includes(expectedName));await device.close();
  }
  else assert.equal(state.commands[`release-offline-${api}`]?.apkSha256,apk.sha256,'First offline run must use the same APK.');
  for(const scale of ['1.0','2.0']){
    const completed=prior?.assertions.some(item=>item.id===`font-${scale}.labels-above-system-bar`&&item.status==='PASS');
    const density=Number(identity.density.match(/(?:Override|Physical) density:\s*(\d+)/)?.[1])/160;
    if(completed){const saved=prior.evidence.find(item=>item.path.endsWith(`/label-bounds-${scale}.json`));assert.ok(saved);const labels=JSON.parse(fs.readFileSync(saved.path,'utf8'));check(`font-${scale}.glyph-height`,true,labels.every(node=>node.bottom-node.top>=Math.floor(12*Number(scale)*density)-2));continue;}
    device.adb(['shell','settings','put','system','font_scale',scale]);device.adb(['shell','am','force-stop',device.package]);await device.open();await device.waitSource(source=>source.includes('plan.create'));const ui=await device.save(`font-${scale}`),bars=await device.request(device.endpoint('appium/device/system_bars'));store(`system-bars-${scale}.json`,bars);
    const actualScale=device.adb(['shell','settings','get','system','font_scale']).trim();check(`font-${scale}.scale`,Number(scale),Number(actualScale));
    const screenHeight=Number(identity.display.match(/(?:Override|Physical) size:\s*\d+x(\d+)/)?.[1]);
    const labels=['今日','日历','计划'].map(label=>nodes(ui).filter(node=>node.text===label&&node.displayed==='true').map(node=>({label,...rect(node.bounds)})).filter(node=>node.top>screenHeight/2)).flat();store(`label-bounds-${scale}.json`,labels);
    check(`font-${scale}.labels`,['今日','日历','计划'],['今日','日历','计划'].filter(label=>labels.some(node=>node.label===label)));
    const navigation=bars.navigationBar;assert.ok(navigation?.visible,'This regression profile requires visible system navigation bars.');
    check(`font-${scale}.labels-above-system-bar`,true,labels.every(node=>node.bottom<=navigation.y));
    check(`font-${scale}.glyph-height`,true,labels.every(node=>node.bottom-node.top>=Math.floor(12*Number(scale)*density)-2));
    await device.close();
  }
}
main().catch(async error=>{assertions.push({id:'execution',status:'FAIL',expected:'layout scope complete',actual:error.message});console.error(error.message);try{if(device.sessionId)await device.save('failure');}catch{}process.exitCode=1;}).finally(async()=>{
  try{await device.close();}catch{}if(originalScale)try{device.adb(['shell','settings','put','system','font_scale',originalScale]);}catch(error){assertions.push({id:'restore-scale',status:'FAIL',actual:error.message});process.exitCode=1;}
  if(originalConnectivity)try{device.adb(['shell','cmd','connectivity','airplane-mode',originalConnectivity.airplane_mode_on==='1'?'enable':'disable']);device.adb(['shell','svc','wifi',originalConnectivity.wifi_on==='1'?'enable':'disable']);device.adb(['shell','svc','data',originalConnectivity.mobile_data==='1'?'enable':'disable']);store('connectivity-restored.json',Object.fromEntries(Object.keys(originalConnectivity).map(key=>[key,device.adb(['shell','settings','get','global',key]).trim()])));}catch(error){assertions.push({id:'restore-connectivity',status:'FAIL',actual:error.message});process.exitCode=1;}
  const evidence=[...reusedEvidence,...fs.readdirSync(directory).filter(name=>name!=='assertions.json').map(name=>({path:`${directory}/${name}`,sha256:sha(fs.readFileSync(`${directory}/${name}`))}))],status=assertions.some(item=>item.status==='FAIL')?'FAIL':'PASS',result={status,api:Number(api),startedAt,endedAt:new Date().toISOString(),apkSha256:apk.sha256,buildRecord:build.record,previousRecord:previous?.record||null,scope:'bottom-tab safety and visible text bounds at baseline viewport with 100%/200% font; Android bounds represent visible text rather than configured line-height box; only affected layout regression, not full matrix or TalkBack',assertions,evidence};
  store('assertions.json',assertions);store('result.json',result);store('evidence-manifest.json',[...evidence,...['assertions.json','result.json'].map(name=>({path:`${directory}/${name}`,sha256:sha(fs.readFileSync(`${directory}/${name}`))}))]);progress.update(s=>{s.commands[`navigation-layout-${api}`]={...result,record:`${directory}/result.json`};s.tasks.find(task=>task.id==='IP27').evidence.push(`${directory}/result.json`);});console.log(`${status}: ${directory}/result.json`);
});
