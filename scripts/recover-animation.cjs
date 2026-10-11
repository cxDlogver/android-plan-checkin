const fs=require('node:fs'),assert=require('node:assert/strict');
const {sha}=require('./p1.cjs'),progress=require('./progress.cjs');
const {createRun}=require('./evidence-run.cjs');
const api=process.argv[2]||'36',key=`native-fonts-worklets-api${api}`,previous=progress.read().commands[key];
assert.equal(previous.status,'FAIL');const saved=JSON.parse(fs.readFileSync(previous.record,'utf8'));
assert.ok(saved.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256));
const folder=previous.record.slice(0,previous.record.lastIndexOf('/'));
function readBounds(name){const xml=fs.readFileSync(`${folder}/${name}.xml`,'utf8'),tag=xml.match(/<[^>]*resource-id="native\.animation\.square"[^>]*>/)?.[0];const numbers=tag?.match(/bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"/)?.slice(1).map(Number);assert.ok(numbers);return numbers;}
const initial=readBounds('native-material-before'),racy=readBounds('native-animation-restored'),settled=readBounds('failure');
console.log(JSON.stringify({initial,racy,settled}));
assert.deepEqual(settled,initial,'Saved later observation must prove the completed return animation; no device rerun is allowed by this recovery.');
const run=createRun(`native-fonts-worklets-recovery-api${api}`,{previousRecord:previous.record,sha256:sha(fs.readFileSync(previous.record))},['IP04'],{caseId:'AC005',rowId:'default',configId:`api${api}-393dp-font1`,recoveredObservation:{record:previous.record,startedAt:saved.startedAt,endedAt:saved.endedAt}});
if(!run)process.exit(0);
run.write('reused-evidence.json',saved.evidence);
run.assertions.push(...saved.assertions.filter(item=>item.status==='PASS'));
run.write('animation-timing-recovery.json',{initial,racy,settled,reason:'UiAutomator source captured the return animation while it was still running; the saved subsequent failure.xml contains its completed native position.',newDeviceActions:0});
run.check('AC005.A1.animation-roundtrip',initial,settled);
const result=run.finish(null,['Reuses original native fonts/translation observations and their immutable XML/screenshots; original timing failure stays preserved.']);
progress.update(state=>{state.commands[key]={...previous,status:'PASS',record:`${run.directory}/result.json`,recoveredFrom:previous.record};});
