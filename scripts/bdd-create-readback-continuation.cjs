const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {runCases}=require('./bdd-ui-session.cjs'),{sha}=require('./p1.cjs'),{passed,combos}=require('./run-bdd-matrix.cjs');
async function main(){
  const config=process.argv[2];assert.ok(combos[config]);const definitions={AC120:{}};
  for(const row of ['weekly','one']){
    const key=`AC120-${row}-${config}`;if(passed(key)){console.log(`REUSE ${key}`);continue;}
    const previous=require('./progress.cjs').read().commands[key];assert.ok(previous?.record,'A committed creation prefix is required.');
    const report=JSON.parse(fs.readFileSync(previous.record,'utf8')),origin=path.dirname(previous.record).replaceAll('\\','/');
    const required=['AC120.A2.unique-plan','AC120.A1.fields','AC120.A3.kind','AC120.A1.rule'];
    assert.ok(required.every(id=>report.assertions.some(a=>a.id===id&&a.status==='PASS')),'Never repeat an already committed CreatePlan When.');
    for(const e of report.evidence)assert.equal(sha(fs.readFileSync(e.path)),e.sha256);
    const before=JSON.parse(fs.readFileSync(`${origin}/before-facts.json`)).snapshot,after=JSON.parse(fs.readFileSync(`${origin}/after-facts.json`)).snapshot;
    const added=after.facts.plans.filter(p=>!before.facts.plans.some(b=>b.id===p.id));assert.equal(added.length,1);const plan=added[0];
    definitions.AC120[row]=async t=>{
      t.run.write('reused-successful-create-prefix.json',{record:previous.record,sha256:sha(fs.readFileSync(previous.record)),assertions:report.assertions.filter(a=>a.status==='PASS'),evidence:report.evidence,scope:'The native CreatePlan save and its four fact assertions are inherited. Only previously unfinished list and Today readbacks execute.'});
      for(const a of report.assertions.filter(a=>a.status==='PASS'))t.run.assertions.push(a);
      for(const file of ['before-facts.json','after-facts.json'])t.run.write(file,fs.readFileSync(`${origin}/${file}`,'utf8'));
      await t.client.call('factsFixture',{facts:after.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});t.run.write('given-restored-committed-facts.json',after.facts);
      await t.nav('/(tabs)/plans');await t.device.seek(`plan.detail.${plan.id}`,true);await t.frame('list-readback');
      await t.nav('/(tabs)/today');await t.device.seek(`record.new.${plan.id}`,true);await t.frame('today-readback');
      t.check('AC120.A3.list-and-today-native-readbacks',true,true);
    };
  }
  if(Object.keys(definitions.AC120).length)await runCases(combos[config][0],definitions,[],config);
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
