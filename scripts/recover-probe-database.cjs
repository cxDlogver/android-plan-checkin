const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const {DatabaseSync}=require('node:sqlite');
const {sha}=require('./p1.cjs'),progress=require('./progress.cjs');
const api=process.argv[2]||'36',report=progress.read().commands[`native-schema_too_new-api${api}`].record;
const directory=path.dirname(report),files=JSON.parse(fs.readFileSync(`${directory}/private-database-artifacts.json`,'utf8'));
const reference=files.find(file=>file.path.endsWith('plan-checkin.db')),bytes=fs.readFileSync(reference.path);
if(files.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256)){console.log('SKIP original probe artifacts are intact');process.exit(0);}
// Earlier cleanup only changed SQLite's page-one header. Recovery succeeds only with the recorded exact SHA256.
const counter=bytes.readUInt32BE(24),validFor=bytes.readUInt32BE(92),library=bytes.readUInt32BE(96);
let recovered=sha(bytes)===reference.sha256?bytes:null;
for(const change of [counter,counter-1,counter-2])for(const valid of [validFor,validFor-1,validFor-2])for(const sqlite of [library,3050003])for(const mode of [[2,2],[1,1]]){
  const candidate=Buffer.from(bytes);candidate.writeUInt32BE(2,60);candidate.writeUInt32BE(change,24);candidate.writeUInt32BE(valid,92);candidate.writeUInt32BE(sqlite,96);candidate[18]=mode[0];candidate[19]=mode[1];
  if(sha(candidate)===reference.sha256)recovered=candidate;
}
assert.ok(recovered,'No reconstruction may be published unless every byte matches the original recorded SHA256.');
const backup=path.join(path.dirname(reference.path),'restore-before-recovery.db');if(sha(bytes)!==reference.sha256){fs.copyFileSync(reference.path,backup);fs.writeFileSync(reference.path,recovered);}
const auxiliaries=files.filter(file=>file!==reference),recoveredAux=[];
if(auxiliaries.some(file=>!fs.existsSync(file.path))){
  const database=new DatabaseSync(reference.path,{readOnly:true});
  try{const tables=JSON.parse(fs.readFileSync(`${directory}/stopped-database-readback.json`,'utf8')).facts;for(const table of Object.keys(tables))database.prepare(`SELECT * FROM ${table}`).all();database.prepare("SELECT name,sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name").all();database.prepare('PRAGMA user_version').get();database.prepare('PRAGMA foreign_key_check').all();for(const file of auxiliaries){const content=fs.readFileSync(file.path);assert.equal(sha(content),file.sha256,'Local SQLite-generated sidecars must match their original hashes exactly.');recoveredAux.push({file,content});}}finally{database.close();}
  for(const item of recoveredAux)fs.writeFileSync(item.file.path,item.content);
}
assert.ok(files.every(file=>sha(fs.readFileSync(file.path))===file.sha256));
const recovery={recordedAt:new Date().toISOString(),report,reason:'Test cleanup modified the local stopped-database copy; restored its exact original bytes by reversing only the recorded page-one changes and matching its original SHA256. Local readback-generated empty WAL/SHM were deterministically recreated with their original hashes; they are host inspection caches, not additional native observations.',database:reference,cleanupCopy:backup,artifacts:files,newDeviceActions:0};
const target=`${directory}/database-byte-recovery.json`;fs.writeFileSync(target,JSON.stringify(recovery,null,2)+'\n');
console.log(`PASS original database byte recovery; ${target}`);
