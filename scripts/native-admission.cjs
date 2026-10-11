const fs=require('node:fs');
const path=require('node:path');
const {DatabaseSync}=require('node:sqlite');
const {sha,snapshot}=require('./p1.cjs');
const {createRun}=require('./evidence-run.cjs');
const {DeviceDriver}=require('./device-driver.cjs');
const {VerificationClient,waitForMetro}=require('./verification-bridge.cjs');
const api=process.argv[2]||'36',mode=process.argv[3]||'visual-guard';
if(!['visual-guard','schema'].includes(mode))throw new Error('Specify visual-guard or schema');
const client=new VerificationClient(api),device=new DeviceDriver(api,'.cache/verification-bridge/admission');
function bounds(source){const tag=source.match(/<[^>]*resource-id="native\.animation\.square"[^>]*>/)?.[0];const values=tag?.match(/bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/)?.slice(1).map(Number);if(!values)throw new Error('Native animation bounds unavailable');return values;}
function logical(value){if(Array.isArray(value))return value.map(logical).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,value])=>[key,logical(value)]));return value;}
async function launch(){
  await waitForMetro();
  device.identity();await device.open();
  device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');
  await device.waitSource(source=>source.includes('今日')||source.includes('原生模块验证'),120000);
  device.deepLink('plancheckin-dev://native');await device.waitSource(source=>source.includes('原生模块验证'),90000);
  await client.waitReady();
}
async function finish(run,operation,limitations=[]){let error=null;try{await operation();}catch(failure){error=failure;console.error(failure.message);try{if(device.sessionId)await device.save('failure');}catch{}}return run.finish(error,limitations);}
async function main(){
  await launch();
  if(mode==='visual-guard'){
    const run=createRun(`native-fonts-worklets-api${api}`,{api,source:snapshot(['src/verification/development.tsx','src/ui/metal.tsx','app/_layout.tsx','assets/fonts'])},['IP04'],{caseId:'AC005',rowId:'default',configId:`api${api}-393dp-font1`});
    if(run){device.directory=run.directory;await finish(run,async()=>{
      run.write('device.json',device.identity());const capture=await client.call('capture');run.write('native-fonts.json',{contextId:capture.contextId,fonts:capture.fonts});
      run.check('AC005.A1.native-fonts-loaded',[{name:'NotoSC400',loaded:true},{name:'NotoSC600',loaded:true},{name:'NotoSC700',loaded:true}],capture.fonts);
      const before=await device.save('native-material-before'),start=bounds(before);
      run.check('AC005.A1.three-weight-labels',true,[400,600,700].every(weight=>before.includes(`计划打卡 中文字体 ${weight}`)));
      const dpi=Number(device.adb(['shell','wm','density']).match(/Physical density:\s*(\d+)/)[1]);
      await device.click('native.animation');await device.waitSource(source=>bounds(source)[0]===start[0]+120*dpi/160);
      const after=await device.save('native-animation-after'),end=bounds(after);
      run.write('worklets-bounds.json',{start,end,dpi,expectedTranslationDp:120,actualTranslationPixels:end[0]-start[0]});
      run.check('AC005.A1.worklets-native-translation',120*dpi/160,end[0]-start[0]);
      await device.click('native.animation');await device.waitSource(source=>JSON.stringify(bounds(source))===JSON.stringify(start));
      run.check('AC005.A1.animation-roundtrip',start,bounds(await device.save('native-animation-restored')));
    },['AC005 visual review and release/offline evidence are linked separately; this report verifies fonts and native Worklets only.']);}
    const connection=createRun(`native-single-connection-api${api}`,{api,source:snapshot(['src/application/service.ts','src/infrastructure/database/executor.ts','src/verification/initialization-development.ts'])},['IP04','IP08'],{caseId:'AC010',rowId:'default',configId:`api${api}-393dp-font1`});
    if(connection){device.directory=connection.directory;await finish(connection,async()=>{
      const result=await client.call('connectionInfo');connection.write('native-connection.json',result);
      connection.check('AC010.A1.successful-executor-attachments',1,result.observation.attachments);
      connection.check('AC010.A1.concurrent-bootstrap-service',true,result.observation.sameService);
      connection.check('AC010.A1.bootstrap-requests',5,result.observation.requests);
      const files=['src/infrastructure/database/executor.ts','src/application/service.ts','app/_layout.tsx'];
      for(const file of files)connection.write(path.basename(file)+'.source.txt',fs.readFileSync(file,'utf8'));
      const executor=fs.readFileSync(files[0],'utf8'),service=fs.readFileSync(files[1],'utf8'),root=fs.readFileSync(files[2],'utf8');
      connection.check('AC010.A1.production-open-site',1,(executor.match(/await openDatabaseAsync\(/g)||[]).length);
      connection.check('AC010.A1.cached-startup',true,service.includes('startup??=DatabaseExecutor.open()'));
      connection.check('AC004.A3.one-provider',1,(root.match(/<AppProvider>/g)||[]).length);
      connection.check('AC004.A3.no-concurrent-checkpoint',false,/wal_checkpoint/i.test(executor+service));
    },['The initial-admission probe closes the original connection before its controlled reopen; no second live business connection is introduced.']);}
  }
  const kind=mode==='schema'?'schema_too_new':'invalid_parameters',caseId=mode==='schema'?'AC009':'AC004';
  const run=createRun(`native-${kind}-api${api}`,{api,kind,source:snapshot(['src/verification/initialization-development.ts','src/infrastructure/database/executor.ts'])},[mode==='schema'?'IP07':'IP04'],{caseId,rowId:'default',configId:`api${api}-393dp-font1`});
  if(!run)return;
  device.directory=run.directory;
  await finish(run,async()=>{
    run.write('device.json',device.identity());const response=await client.call('initializationProbe',{kind,confirm:'CLOSE_ISOLATED_DEV_CONNECTION'}),data=response.observation;run.write('native-initialization.json',response);
    run.check(`${caseId}.blocked-code`,kind==='schema_too_new'?'SCHEMA_TOO_NEW':'INIT_FAILED',data.code);
    run.check(`${caseId}.no-writable-handle`,false,data.handedOut);
    if(kind==='invalid_parameters')run.check('AC004.A3.actual-mismatched-pragma',{journal_mode:'delete'},data.observedJournal);
    device.adb(['shell','am','force-stop',device.package]);
    const folder=`.artifacts/probes/${path.basename(path.dirname(run.directory))}/${kind}-api${api}`;fs.mkdirSync(folder,{recursive:true});
    const remote='/data/user/0/com.xiang.plancheckin.dev/files/SQLite/plan-checkin.db',local=`${folder}/plan-checkin.db`;
    const listing=device.adb(['shell','run-as',device.package,'ls','-l','files/SQLite']);run.write('private-files-after.log',listing);
    const pulled=[];
    device.adb(['pull',remote,local]);
    pulled.push(local);
    for(const suffix of ['-wal','-shm'])if(listing.includes(`plan-checkin.db${suffix}`)){device.adb(['pull',remote+suffix,local+suffix]);pulled.push(local+suffix);}
    run.write('private-database-artifacts.json',pulled.map(file=>({path:file,sha256:sha(fs.readFileSync(file))})));
    const readbackFolder=`${folder}/readback`;fs.mkdirSync(readbackFolder,{recursive:true});
    for(const file of pulled)fs.copyFileSync(file,`${readbackFolder}/${path.basename(file)}`);
    const readbackFile=`${readbackFolder}/plan-checkin.db`,database=new DatabaseSync(readbackFile,{readOnly:true});
    let observed;
    try{observed={facts:Object.fromEntries(Object.keys(data.before.facts).map(table=>[table,database.prepare(`SELECT * FROM ${table}`).all()])),schema:database.prepare("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name").all(),userVersion:database.prepare('PRAGMA user_version').get(),foreignKeyCheck:database.prepare('PRAGMA foreign_key_check').all()};}finally{database.close();}
    run.write('stopped-database-readback.json',observed);
    run.check(`${caseId}.facts-preserved`,sha(JSON.stringify(logical(data.before.facts))),sha(JSON.stringify(logical(observed.facts))));
    run.check(`${caseId}.schema-preserved`,data.before.schema,observed.schema);
    run.check(`${caseId}.version-preserved`,{user_version:kind==='schema_too_new'?2:1},observed.userVersion);
    run.check(`${caseId}.foreign-keys`,[],observed.foreignKeyCheck);
    if(kind==='schema_too_new'){
      // Test cleanup restores only the deliberately raised version, after all immutable observations.
      const restoreFolder=`${folder}/restore`;fs.mkdirSync(restoreFolder,{recursive:true});
      for(const suffix of ['','-wal','-shm'])if(fs.existsSync(readbackFile+suffix))fs.copyFileSync(readbackFile+suffix,`${restoreFolder}/plan-checkin.db${suffix}`);
      const restoreFile=`${restoreFolder}/plan-checkin.db`,restore=new DatabaseSync(restoreFile);try{restore.exec('PRAGMA user_version=1; PRAGMA wal_checkpoint(TRUNCATE);');}finally{restore.close();}
      const staged='/data/local/tmp/plancheckin-restore-schema.db';device.adb(['push',restoreFile,staged]);device.adb(['shell','chmod','644',staged]);
      device.adb(['shell','run-as',device.package,'rm','-f','files/SQLite/plan-checkin.db-wal','files/SQLite/plan-checkin.db-shm']);
      device.adb(['shell','run-as',device.package,'cp',staged,'files/SQLite/plan-checkin.db']);device.adb(['shell','run-as',device.package,'chmod','600','files/SQLite/plan-checkin.db']);device.adb(['shell','rm','-f',staged]);
      run.write('cleanup.json',{scope:'restore the deliberate test-only user_version change on stopped .dev app',user_version:1,factsChanged:false});
    }
  },[kind==='invalid_parameters'?'Development probe changes the real SQLite journal PRAGMA after initialization and reads it back; it does not simulate a physical storage failure.':'Actual initialization-service high-schema refusal; error page layout remains separate AC082.']);
}
main().catch(error=>{console.error(error.message);process.exitCode=1;}).finally(async()=>{try{await device.close();}catch{}});
