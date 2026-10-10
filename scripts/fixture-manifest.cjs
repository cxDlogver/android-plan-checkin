const fs=require('node:fs'),{DatabaseSync}=require('node:sqlite'),{createHash}=require('node:crypto');
const {buildFixture,fixtureNames,fixtureSeed,fixtureVersion}=require('../.artifacts/integration/src/verification/fixtures.js');
const {schemaV1}=require('../.artifacts/integration/src/infrastructure/database/schema.js');
const today=process.argv[2]||'2026-10-10',zone=process.argv[3]||'Asia/Shanghai';
if(!/^\d{4}-\d{2}-\d{2}$/.test(today)||!/^[A-Za-z0-9_+/-]+$/.test(zone))throw new Error('Invalid fixture date or zone path');
const directory=`.artifacts/fixtures/v${fixtureVersion}/${zone.replaceAll('/','_')}/${today}`;fs.mkdirSync(directory,{recursive:true});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const fixtures=[];
for(const name of fixtureNames){
  const facts=buildFixture(name,today,zone),json=JSON.stringify(facts),file=`${directory}/${name}.db`;
  if(fs.existsSync(file))fs.unlinkSync(file);
  const database=new DatabaseSync(file);database.exec('PRAGMA foreign_keys=ON; BEGIN IMMEDIATE;');
  try{database.exec(schemaV1);for(const [table,rows] of Object.entries(facts))for(const row of rows){const columns=Object.keys(row);database.prepare(`INSERT INTO ${table} (${columns.join(',')}) VALUES (${columns.map(()=>'?').join(',')})`).run(...columns.map(column=>row[column]));}database.exec('PRAGMA user_version=1; COMMIT;');}catch(error){database.exec('ROLLBACK');throw error;}finally{database.close();}
  fixtures.push({name,version:fixtureVersion,seed:fixtureSeed(name,today,zone),today,zone,rowCounts:Object.fromEntries(Object.entries(facts).map(([table,rows])=>[table,rows.length])),planTypes:Object.fromEntries(['fixed','weekly','one_time'].map(type=>[type,facts.plans.filter(plan=>plan.type===type).length])),factsSha256:sha(json),database:{path:file,sha256:sha(fs.readFileSync(file)),bytes:fs.statSync(file).size}});
}
fs.writeFileSync('resource/progress/fixture-manifest.json',JSON.stringify({recordedAt:new Date().toISOString(),scope:'versioned disposable test facts; native private-directory load validation remains separate',fixtures},null,2)+'\n');
console.log(`Generated ${fixtures.length} deterministic databases and fixture manifest.`);
