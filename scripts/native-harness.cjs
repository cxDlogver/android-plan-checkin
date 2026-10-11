const fs=require('node:fs');
const {DatabaseSync}=require('node:sqlite');
const {sha,snapshot}=require('./p1.cjs');
const {DeviceDriver}=require('./device-driver.cjs');
const {VerificationClient}=require('./verification-bridge.cjs');
const {createRun}=require('./evidence-run.cjs');
const progress=require('./progress.cjs');
const api=process.argv[2]||'36';
const manifest=JSON.parse(fs.readFileSync('resource/progress/fixture-manifest.json','utf8'));
const fixture=manifest.fixtures.find(row=>row.name==='F01');
const build=progress.read().commands['native-debug'];
const inputs={api,fixture,apk:build.artifacts.find(file=>file.path.endsWith('.apk')),source:snapshot(['src/verification','scripts/verification-bridge.cjs','scripts/native-harness.cjs','scripts/evidence-run.cjs'])};
const run=createRun(`native-harness-api${api}`,inputs,['IP05']);
if(!run)process.exit(0);
const device=new DeviceDriver(api,run.directory),client=new VerificationClient(api);
function canonicalFacts(facts){return JSON.stringify(Object.fromEntries(Object.entries(facts).sort(([a],[b])=>a.localeCompare(b)).map(([table,rows])=>[table,rows.map(row=>Object.fromEntries(Object.entries(row).sort(([a],[b])=>a.localeCompare(b)))).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))])));}
async function main(){
  run.write('device.json',device.identity());
  const installed=device.adb(['shell','pm','path',device.package]).trim();
  if(!installed.startsWith('package:'))throw new Error('Existing signed development APK is required');
  run.write('installed-package.log',installed);
  run.check('AC006.A4.fixture-byte-identity',fixture.database.sha256,sha(fs.readFileSync(fixture.database.path)));
  const expectedDb=new DatabaseSync(fixture.database.path,{readOnly:true});
  let expectedFacts;
  try{expectedFacts=Object.fromEntries(Object.keys(fixture.rowCounts).map(table=>[table,expectedDb.prepare(`SELECT * FROM ${table}`).all()]));}finally{expectedDb.close();}
  // Identity guard is checked before any stop/copy operation. This is the disposable .dev database.
  device.adb(['shell','am','force-stop',device.package]);
  run.write('root.log',device.adb(['root']));device.adb(['wait-for-device']);
  run.write('root-identity.json',{...device.identity(),adbUid:device.adb(['shell','id','-u']).trim()});
  run.check('AC006.A4.root-available','0',device.adb(['shell','id','-u']).trim());
  const remote='/data/local/tmp/plancheckin-fixture-F01.db',target='files/SQLite/plan-checkin.db';
  device.adb(['push',fixture.database.path,remote]);
  device.adb(['shell','chmod','644',remote]);
  // Keep the stopped original database and both WAL sidecars under the app's own private uid.
  device.adb(['shell','run-as',device.package,'mkdir','-p','files/SQLite/harness-backup']);
  for(const suffix of ['', '-wal','-shm']){
    try{device.adb(['shell','run-as',device.package,'cp',target+suffix,`files/SQLite/harness-backup/plan-checkin.db${suffix}`]);}catch(error){run.write(`optional-backup${suffix||'-main'}.log`,error.message);}
  }
  device.adb(['shell','run-as',device.package,'rm','-f',target+'-wal',target+'-shm']);
  device.adb(['shell','run-as',device.package,'cp',remote,target]);
  device.adb(['shell','run-as',device.package,'chmod','600',target]);
  const uid=device.adb(['shell','run-as',device.package,'id','-u']).trim();
  const stat=device.adb(['shell','run-as',device.package,'stat','-c','%u:%g:%a',target]).trim();
  const fileHash=device.adb(['shell','run-as',device.package,'sha256sum',target]).trim().split(/\s/)[0];
  run.write('private-load.json',{applicationId:device.package,stopped:true,target,uid,stat,fileHash,fixtureDatabase:fixture.database,backupDirectory:'files/SQLite/harness-backup'});
  run.check('AC006.A4.private-file-owner-and-mode',`${uid}:${uid}:600`,stat);
  run.check('AC006.A4.private-file-sha256',fixture.database.sha256,fileHash);
  device.adb(['shell','rm','-f',remote]);
  device.adb(['reverse','tcp:8081','tcp:8081']);device.adb(['reverse','tcp:8097','tcp:8097']);
  await device.open();
  device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');
  let source=await device.waitSource(source=>source.includes('今日')||source.includes('Continue')||source.includes('Unable to load'),120000);
  if(source.includes('text="Continue"')){await device.text('Continue');source=await device.source();if(source.includes('content-desc="Close"')){const close=await device.element('accessibility id','Close');await device.request(device.endpoint(`element/${close}/click`),'POST',{});}}
  await device.waitSource(source=>source.includes('今日'),120000);
  device.deepLink('plancheckin-dev://native');
  await device.waitSource(source=>source.includes('原生模块验证'),90000);
  run.write('bridge-identity.json',await client.waitReady());
  const instant=`${fixture.today}T04:00:00Z`;
  run.write('clock-applied.json',await client.call('clock',{instant}));
  const observation=await client.call('capture');run.write('private-load-readback.json',observation);
  run.check('AC006.A4.native-private-load-facts',sha(canonicalFacts(expectedFacts)),sha(canonicalFacts(observation.snapshot.facts)));
  run.check('AC006.A3.clock-native-readback',Date.parse(instant),observation.snapshot.asOfMs);
  const context=observation.contextId;
  await client.call('navigate',{route:'/(tabs)/today'});await device.waitSource(source=>source.includes('今日')&&!source.includes('原生模块验证'));
  const after=await client.call('capture');run.write('clock-after-navigation.json',after);
  run.check('clock-context-retained',context,after.contextId);
  run.check('clock-instant-retained',Date.parse(instant),after.snapshot.asOfMs);
  await device.save('clock-today');
  const denied=await fetch('http://127.0.0.1:8098/request',{method:'POST',headers:{'content-type':'application/json','origin':'https://example.invalid'},body:JSON.stringify({action:'fixture',api:Number(api),payload:{}})});
  run.check('bridge-browser-reset-rejected',403,denied.status);
  const system=await client.call('clock',{instant:null});run.write('clock-restored.json',system);
  run.check('clock-restored-near-system',true,Math.abs(system.clock-Date.now())<10000);
}
let error=null;
main().catch(async failure=>{error=failure;console.error(failure.message);try{if(device.sessionId)await device.save('failure');}catch{}}).finally(async()=>{
  try{await client.call('fault',{point:null});await client.call('clock',{instant:null});}catch{}
  try{await device.close();}catch(failure){error??=failure;}
  run.finish(error,['AC006 parent awaits both APIs and existing release exclusion evidence; performance fixture timing remains separate AC096','Private load uses stopped disposable .dev app; preserved previous developer database under app-owned harness-backup']);
});
