const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{DatabaseSync}=require('node:sqlite'),{execFileSync}=require('node:child_process'),progress=require('./progress.cjs'),{env,toolRoot}=require('./task-env.cjs');
const {sha,snapshot}=require('./p1.cjs'),{createRun}=require('./evidence-run.cjs'),{DeviceDriver}=require('./device-driver.cjs'),{VerificationClient,waitForMetro}=require('./verification-bridge.cjs');
const api=process.argv[2]||'36',device=new DeviceDriver(api,'.cache/verification-bridge/migrations');let client=new VerificationClient(api);
function logical(value){if(Array.isArray(value))return value.map(logical).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,value])=>[key,logical(value)]));return value;}
const digest=value=>sha(JSON.stringify(logical(value)));
async function launch(){await waitForMetro();device.adb(['reverse','tcp:8081','tcp:8081']);await device.open();device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');await device.waitSource(source=>source.includes('今日')||source.includes('原生模块验证'),120000);device.deepLink('plancheckin-dev://native');await device.waitSource(source=>source.includes('原生模块验证'));await client.waitReady();const ready=await client.status();assert.ok(ready.hello.capabilities.includes('migrationProbe'));return ready;}
async function settled(kind){const deadline=Date.now()+25000;while(Date.now()<deadline){const response=await client.call('migrationStatus');if(response.observation.phase===(kind==='sql_error'?'finished':'before_commit'))return response;assert.notEqual(response.observation.phase,'failed');await new Promise(resolve=>setTimeout(resolve,250));}throw new Error('Migration probe did not reach its fault point');}
function pullStopped(run,before){
  const folder=`.artifacts/probes/${path.basename(path.dirname(run.directory))}/migration-api${api}`;fs.mkdirSync(folder,{recursive:true});
  const remote='/data/user/0/com.xiang.plancheckin.dev/files/SQLite/plan-checkin.db',local=`${folder}/plan-checkin.db`,listing=device.adb(['shell','run-as',device.package,'ls','-l','files/SQLite']);run.write('stopped-private-files.log',listing);
  const files=[];for(const suffix of ['','-wal','-shm'])if(!suffix||listing.includes(`plan-checkin.db${suffix}`)){
    const bytes=execFileSync(path.join(toolRoot,'sdk/platform-tools/adb.exe'),['-s',device.serial,'exec-out','run-as',device.package,'cat',`files/SQLite/plan-checkin.db${suffix}`],{env,timeout:30000,windowsHide:true,maxBuffer:16*1024*1024});fs.writeFileSync(local+suffix,bytes);files.push(local+suffix);
  }
  run.write('raw-private-artifacts.json',files.map(file=>({path:file,sha256:sha(fs.readFileSync(file))})));
  const copy=`${folder}/readback`;fs.mkdirSync(copy,{recursive:true});for(const file of files)fs.copyFileSync(file,`${copy}/${path.basename(file)}`);
  const db=new DatabaseSync(`${copy}/plan-checkin.db`,{readOnly:true});try{return {facts:Object.fromEntries(Object.keys(before.facts).map(table=>[table,db.prepare(`SELECT * FROM ${table}`).all()])),schema:db.prepare("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name").all(),version:db.prepare('PRAGMA user_version').get(),foreignKeyCheck:db.prepare('PRAGMA foreign_key_check').all()};}finally{db.close();}
}
async function main(){
  device.identity();await launch();
  await client.call('clock',{instant:'2026-10-11T04:00:00Z'});await client.call('fixture',{name:'F01',zone:'Asia/Shanghai',confirm:'RESET_ISOLATED_DEV_DATABASE'});
  for(const kind of ['sql_error','process_before_commit']){
    const run=createRun(`AC008-${kind}-api${api}`,{api,kind,source:snapshot(['src/infrastructure/database/migrations.ts','src/verification/migration-development.ts','scripts/native-migrations.cjs'])},['IP07'],{caseId:'AC008',rowId:kind,configId:`api${api}-393dp-font1`,fr:['FR32'],at:['AT24']});if(!run)continue;
    device.directory=run.directory;let error=null;
    try{
      run.write('device.json',device.identity());run.write('bridge-identity.json',await client.status());
      run.write('started.json',await client.call('migrationProbe',{kind,confirm:'MIGRATE_ISOLATED_DEV_DATABASE'}));
      const response=await settled(kind),data=response.observation;run.write('native-migration-observation.json',response);
      run.check('both-pending-steps-executed',true,['migration_probe_one','migration_probe_two'].every(name=>data.pending.schema.some(table=>table.name===name)));
      run.check('first-step-facts-were-changed',true,digest(data.before.facts)!==digest(data.pending.facts));
      let after;
      if(kind==='sql_error'){run.check('migration-service-failure','MIGRATION_FAILED',data.code);after=data.after;}
      else{
        run.check('uncommitted-final-version',3,data.pendingVersion.user_version);
        const pid=device.adb(['shell','pidof',device.package]).trim();assert.ok(/^\d+$/.test(pid));run.write('process-before.log',pid+'\n');
        device.adb(['shell','am','force-stop',device.package]);run.write('package-stopped.log',device.adb(['shell','dumpsys','package',device.package]).split(/\r?\n/).filter(line=>line.includes('stopped=')).join('\n')+'\n');
        after=pullStopped(run,data.before);run.write('stopped-readback.json',after);
        client=new VerificationClient(api);await device.close();await launch();const reopened=await client.call('capture');run.write('reopened-native.json',reopened);
        run.check('reopen-preserves-previous-facts',digest(data.before.facts),digest(reopened.snapshot.facts));
        run.check('reopened-previous-version',1,reopened.sqlite.userVersion.user_version);
        run.write('process-interruption.json',{oldPid:pid,failure:'PROCESS_INTERRUPTED_BEFORE_COMMIT',oldContext:response.contextId,newContext:reopened.contextId,noMigrationSuccessAcknowledged:true});
        run.check('new-native-process-context',false,response.contextId===reopened.contextId);
      }
      run.write('after.json',after);
      run.check('AC008.A1.version',data.before.version,after.version);run.check('AC008.A1.schema',data.before.schema,after.schema);
      run.check('AC008.A2.logical-facts',digest(data.before.facts),digest(after.facts));run.check('AC008.A2.foreign-keys',[],after.foreignKeyCheck);
      const code=fs.readFileSync('src/infrastructure/database/migrations.ts','utf8')+fs.readFileSync('src/infrastructure/database/executor.ts','utf8');run.write('migration-source.txt',code);
      run.check('AC008.A3.no-destructive-recovery',false,/deleteDatabase|unlink|DROP TABLE|VACUUM|removeAsync/.test(code));
    }catch(failure){error=failure;console.error(failure.message);}
    run.finish(error,['The production all-pending migration function is executed against actual private development SQLite. Versions 2/3 are controlled probe steps, not shipped schema versions.','Process interruption is an actual force-stop before COMMIT. The dead process cannot return an error code; raw stopped-file and native reopen observations establish rollback.','No database/WAL/SHM file is deleted or restored during this verification.']);if(error)break;
  }
}
async function recover(){
  const key=`AC008-process_before_commit-api${api}`,previous=progress.read().commands[key],original=JSON.parse(fs.readFileSync(previous.record,'utf8'));
  assert.equal(original.status,'FAIL');assert.ok(original.assertions.some(item=>item.id==='execution'&&item.actual.includes('Permission denied')));
  assert.ok(original.evidence.every(file=>sha(fs.readFileSync(file.path))===file.sha256));
  const observationPath=original.evidence.find(file=>file.path.endsWith('/native-migration-observation.json')).path,response=JSON.parse(fs.readFileSync(observationPath,'utf8')),data=response.observation;
  const run=createRun(`${key}-recovery`,{original:previous.record,sha256:sha(fs.readFileSync(previous.record))},['IP07'],{caseId:'AC008',rowId:'process_before_commit',configId:`api${api}-393dp-font1`});if(!run)return;
  device.directory=run.directory;let error=null;
  try{
    run.write('device.json',device.identity());run.assertions.push(...original.assertions.filter(item=>item.status==='PASS'));run.write('reused-evidence.json',{record:previous.record,evidence:original.evidence});
    const after=pullStopped(run,data.before);run.write('stopped-readback.json',after);
    run.check('AC008.A1.version',data.before.version,after.version);run.check('AC008.A1.schema',data.before.schema,after.schema);run.check('AC008.A2.logical-facts',digest(data.before.facts),digest(after.facts));run.check('AC008.A2.foreign-keys',[],after.foreignKeyCheck);
    await launch();const reopened=await client.call('capture');run.write('reopened-native.json',reopened);
    run.check('reopen-preserves-previous-facts',digest(data.before.facts),digest(reopened.snapshot.facts));run.check('reopened-previous-version',1,reopened.sqlite.userVersion.user_version);run.check('new-native-process-context',false,response.contextId===reopened.contextId);
    const code=fs.readFileSync('src/infrastructure/database/migrations.ts','utf8')+fs.readFileSync('src/infrastructure/database/executor.ts','utf8');run.write('migration-source.txt',code);run.check('AC008.A3.no-destructive-recovery',false,/deleteDatabase|unlink|DROP TABLE|VACUUM|removeAsync/.test(code));
    run.write('recovery.json',{reason:'The actual before-COMMIT force-stop already succeeded. Raw stopped private files are now read through run-as, without repeating migration or process interruption.',processInterruptionRepeated:false,privateFilesDeleted:false});
  }catch(failure){error=failure;console.error(failure.message);}
  const result=run.finish(error,['Reuses the original pending DDL/data/version observations and actual force-stop. Only failed evidence extraction and remaining native reopen assertions are completed.']);
  if(result.status==='PASS')progress.update(state=>{state.commands[key]={...previous,status:'PASS',record:`${run.directory}/result.json`,recoveredFrom:previous.record};});
}
(process.argv[3]==='recover'?recover():main()).catch(error=>{console.error(error.message);process.exitCode=1;}).finally(async()=>{try{await client.call('clock',{instant:null});}catch{}try{await device.close();}catch{}});
