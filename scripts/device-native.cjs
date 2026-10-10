const fs=require('node:fs');
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {DeviceDriver,reportFromSource}=require('./device-driver.cjs');
const {snapshot}=require('./p1.cjs');
const progress=require('./progress.cjs');
const sha=data=>createHash('sha256').update(data).digest('hex');
const api=process.argv[2]||'36',mode=process.argv[3]||'modules';
assert.ok(['modules','inspect','recover'].includes(mode));
const startedAt=new Date().toISOString(),runId=startedAt.replace(/[:.]/g,'-');
const build=progress.read().commands['native-debug'];
assert.equal(build?.status,'PASS','Build a development APK first.');
const inputSha256=sha(JSON.stringify({api,mode:mode==='recover'?'modules':mode,apk:build.artifacts,source:snapshot(['app/_layout.tsx','src/infrastructure/database','src/domain/date.ts','src/verification/development.tsx','metro.config.cjs'])}));
const previous=progress.read().commands[`native-device-${api}`];
if(mode==='modules'&&previous?.status==='PASS'&&previous.inputSha256===inputSha256&&fs.existsSync(previous.record)){
  const saved=JSON.parse(fs.readFileSync(previous.record,'utf8'));
  if(saved.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256)){console.log(`SKIP native-device-${api}: unchanged passing evidence; ${previous.record}`);process.exit(0);}
}
const directory=`resource/acceptance/runs/${runId}/native-api${api}`;
const device=new DeviceDriver(api,directory);
const assertions=[];
const reusedEvidence=[];
let recoveredObservation=null;
const check=(id,expected,actual)=>{const status=JSON.stringify(actual)===JSON.stringify(expected)?'PASS':'FAIL';assertions.push({id,expected,actual,status});};
function assertReport(report,identity,source){
  check('AC004.A1',{journal_mode:'wal',synchronous:2,foreign_keys:1},{...report.sqlite.journal,...report.sqlite.synchronous,...report.sqlite.foreignKeys});
  check('AC004.A2.versionPresent',true,typeof report.sqlite.version.version==='string'&&report.sqlite.version.version.length>0&&typeof report.sqlite.version.sourceId==='string');
  check('AC004.A2.privatePath',true,report.sqlite.path.some(row=>row.name==='main'&&/\/com\.xiang\.plancheckin\.dev\/.*plan-checkin\.db$/.test(row.file)));
  check('AC005.intl',{shanghai:'2026-10-09',newYork:'2026-03-09',dstHours:23},report.intl);
  check('AC006.A1',{api:Number(api),avd:`plancheckin_api${api}`,serial:device.serial,package:device.package},{api:identity.api,avd:identity.avd,serial:identity.serial,package:source.includes(`package="${device.package}"`)?device.package:null});
}
async function main(){
  if(mode==='recover'){
    assert.equal(previous?.status,'FAIL');
    let reference=previous.record,saved=JSON.parse(fs.readFileSync(reference,'utf8'));
    while(!saved.evidence.some(file=>file.path.endsWith('/failure.xml'))&&saved.previousRecord){reference=saved.previousRecord;saved=JSON.parse(fs.readFileSync(reference,'utf8'));}
    assert.equal(saved.inputSha256,inputSha256,'Recovery cannot reinterpret evidence from different source or APK.');
    recoveredObservation={record:reference,startedAt:saved.startedAt,endedAt:saved.endedAt};
    assert.ok(saved.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256));reusedEvidence.push(...saved.evidence);
    const read=name=>fs.readFileSync(saved.evidence.find(file=>file.path.endsWith(`/${name}`)).path,'utf8');
    const source=read('failure.xml'),report=reportFromSource(source);assert.ok(report,'Saved XML must contain a complete native report.');
    fs.writeFileSync(`${directory}/native-report.json`,JSON.stringify(report,null,2)+'\n');assertReport(report,JSON.parse(read('device.json')),source);return;
  }
  const identity=device.identity();fs.writeFileSync(`${directory}/device.json`,JSON.stringify(identity,null,2)+'\n');
  const apk=build.artifacts?.find(file=>file.path.endsWith('.apk'));assert.ok(apk);assert.equal(sha(fs.readFileSync(apk.path)),apk.sha256,'APK differs from build record');
  fs.writeFileSync(`${directory}/build-reference.json`,JSON.stringify({record:build.record,apk,source:snapshot(['app','src','assets','plugins','package.json','pnpm-lock.yaml'])},null,2)+'\n');
  device.adb(['install','-r',apk.path]);device.adb(['reverse','tcp:8081','tcp:8081']);
  await device.open();
  if(mode==='inspect'){await device.save('inspect');return;}
  device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');
  const startup=await device.waitSource(source=>source.includes('今日')||source.includes('初始化失败')||source.includes('Unable to load')||source.includes('Continue'));
  if(startup.includes('text="Continue"')){await device.text('Continue');const source=await device.source();if(source.includes('content-desc="Close"')){const close=await device.element('accessibility id','Close');await device.request(device.endpoint(`element/${close}/click`),'POST',{});}}
  await device.waitSource(source=>source.includes('今日')||source.includes('初始化失败')||source.includes('Unable to load'),120000);
  await device.save('startup');
  device.deepLink('plancheckin-dev://native');
  await device.waitSource(source=>source.includes('原生模块验证'));
  await device.save('native-top');
  const report=await device.report();fs.writeFileSync(`${directory}/native-report.json`,JSON.stringify(report,null,2)+'\n');
  assertReport(report,identity,await device.source());
  await device.save('native-report');
}
main().catch(async error=>{assertions.push({id:'execution',expected:'successful native execution',actual:error.message,status:'FAIL'});console.error(error.message);try{if(device.sessionId)await device.save('failure');}catch{}process.exitCode=1;}).finally(async()=>{
  try{await device.close();}catch(error){assertions.push({id:'cleanup',expected:'session closed',actual:error.message,status:'FAIL'});process.exitCode=1;}
  const evidence=[...reusedEvidence,...fs.readdirSync(directory).filter(file=>!['result.json','assertions.json','evidence-manifest.json'].includes(file)).map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))];
  const status=assertions.some(item=>item.status==='FAIL')?'FAIL':mode==='inspect'?'NOT_RUN':'PASS';
  const result={runId,status,startedAt,endedAt:new Date().toISOString(),inputSha256,previousRecord:previous?.record||null,recoveredObservation,scope:'development native assertions only',api:Number(api),mode,assertions,evidence,limitations:['AC004 A3 initialization-failure/device guard not fully exercised','AC005 release/offline/fonts/visual review pending','AC006 full fixture and private-directory load chain pending; parent scenarios stay NOT_RUN']};
  fs.writeFileSync(`${directory}/assertions.json`,JSON.stringify(assertions,null,2)+'\n');fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
  fs.writeFileSync(`${directory}/evidence-manifest.json`,JSON.stringify([...evidence,...['result.json','assertions.json'].map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))],null,2)+'\n');
  progress.update(state=>{state.commands[`native-device-${api}`]={status,inputSha256,record:`${directory}/result.json`};for(const id of ['IP04','IP05'])state.tasks.find(task=>task.id===id).evidence.push(`${directory}/result.json`);});
  console.log(`${status}: ${directory}/result.json`);
});
