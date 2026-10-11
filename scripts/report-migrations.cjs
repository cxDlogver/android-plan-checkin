const fs=require('node:fs'),assert=require('node:assert/strict'),{sha}=require('./p1.cjs'),progress=require('./progress.cjs'),{createRun}=require('./evidence-run.cjs'),{link}=require('./link-native-acceptance.cjs');
const state=progress.read();
function read(key,required='PASS'){const command=state.commands[key];assert.equal(command?.status,required,key);const result=JSON.parse(fs.readFileSync(command.record,'utf8'));assert.ok(result.evidence.every(file=>sha(fs.readFileSync(file.path))===file.sha256));return {key,path:command.record,sha256:sha(fs.readFileSync(command.record)),result};}
if(process.argv[2]==='host'){
  const failure=read('migration-tests','FAIL'),success=read('migration-success-test');
  const initialLog=fs.readFileSync(failure.result.evidence.find(file=>file.path.endsWith('/commands.log')).path,'utf8'),finalLog=fs.readFileSync(success.result.evidence.find(file=>file.path.endsWith('/commands.log')).path,'utf8');
  const run=createRun('migration-host-summary',{records:[failure,success].map(({path,sha256})=>({path,sha256}))},['IP07']);if(!run)process.exit(0);
  run.write('reused-evidence.json',[failure,success]);
  run.check('second-SQL-error-whole-chain-rollback',true,/✔ migration chain rolls back first-step DDL and every fact after second SQL error/.test(initialLog));
  run.check('deferred-FK-whole-chain-rollback',true,/✔ migration chain rolls back first-step DDL and every fact after deferred foreign key failure/.test(initialLog));
  run.check('success-version-last-one-commit',true,/✔ migration chain commits once after both validated steps and writes the version last/.test(finalLog));
  run.finish(null,['Host SQLite only; native interruption/API reports are tracked separately. Initial two passing cases are reused; only the failed success-report type assertion was rerun.']);
  progress.update(s=>{s.tasks.find(task=>task.id==='IP07').blockedReason=null;});process.exit(0);
}
const configurations=[];
for(const api of ['29','36'])for(const rowId of ['sql_error','process_before_commit']){
  const ref=read(`AC008-${rowId}-api${api}`);configurations.push({api,rowId,report:ref.path,sha256:ref.sha256});
}
const run=createRun('AC008-migration-summary',{configurations},['IP07'],{caseId:'AC008',configId:'all-required-native-configs'});
if(run){run.write('configuration-reports.json',configurations);for(const config of configurations)run.check(`AC008.${config.rowId}.api${config.api}`,'PASS',JSON.parse(fs.readFileSync(config.report,'utf8')).status);run.finish(null,['Each API executes both original parameter rows. The process row uses an actual force-stop; the dead process cannot return a service error code, and raw/private/native reopen observations verify rollback.']);link('AC008',`${run.directory}/result.json`,configurations,'全链迁移函数真实执行；SQL异常返回MIGRATION_FAILED，提交前实际进程中断以停止库及原生重开证明回滚。失败证据提取仅补录，未重复中断。');}
console.log('AC008 linked across both API/parameter configurations.');
