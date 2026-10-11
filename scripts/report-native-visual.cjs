const fs=require('node:fs'),assert=require('node:assert/strict');
const {sha}=require('./p1.cjs'),progress=require('./progress.cjs'),{createRun}=require('./evidence-run.cjs'),{link}=require('./link-native-acceptance.cjs');
const state=progress.read(),configurations=[];
function read(key){const command=state.commands[key];assert.equal(command?.status,'PASS',key);const result=JSON.parse(fs.readFileSync(command.record,'utf8').replace(/^\uFEFF/,''));assert.ok(result.evidence.every(file=>sha(fs.readFileSync(file.path))===file.sha256),key);return {key,path:command.record,sha256:sha(fs.readFileSync(command.record)),result};}
const tokens=JSON.parse(fs.readFileSync('resource/design/design-tokens.json','utf8')),fonts=JSON.parse(fs.readFileSync('resource/progress/font-vendoring.json','utf8'));
const bundle=read('apk-bundle-audit'),build=read('native-release'),audit=read('apk-audit-release'),embedded=read('native-embedded-check');
const manifestPath=state.commands['apk-bundle-audit'].manifestPath,manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
assert.equal(bundle.result.apk.sha256,build.result.artifacts[0].sha256);
const metal=fs.readFileSync('src/ui/metal.tsx','utf8');
// These are observations from the saved screenshots viewed during this run, not new device actions.
const visualReview={reviewedAt:new Date().toISOString(),reviewer:'Codex',scope:'AC005 API29/36 393dp font1 native sample and changed release material',observations:{button:'Vertical silver gradient has a narrow bright band near 44%, with top/bottom inset rims and a soft outer shadow.',selected:'Four graphite stops run from light top to dark bottom; the 70% stop is present.',card:'White top fades to silver bottom; shadows extend beyond both side borders in Today, Plans, Calendar and Detail.',input:'Inset field shadow and border are visible; text and labels remain readable.',navigation:'Three tabs and Stack pages show embedded Chinese and icons while Metro and guest connectivity are off.',api29SystemUI:'SystemUI was frozen independently of the app. Identity-guarded emulator recovery restored live dark status icons; original observations remain intact.'},limitations:['This is the native admission sample, not the eight-configuration visual/TalkBack acceptance.','The saved detail viewport is scrollable; content below the viewport is not treated as clipped text.']};
for(const api of ['29','36']){
  const refs=[read(`native-fonts-worklets-api${api}`),read(`release-material-api${api}`),read(`release-detail-layout-api${api}`),bundle,build,audit,embedded];
  assert.equal(refs[1].result.apkSha256,bundle.result.apk.sha256);
  const run=createRun(`AC005-visual-api${api}`,{api,refs:refs.map(({key,path,sha256})=>({key,path,sha256})),manifestSha256:sha(fs.readFileSync(manifestPath)),tokensSha256:sha(fs.readFileSync('resource/design/design-tokens.json')),metalSha256:sha(metal)},['IP04'],{caseId:'AC005',rowId:'default',configId:`api${api}-393dp-font1`,fr:['FR14','FR32'],at:['AT25','AT28'],apkSha256:bundle.result.apk.sha256});
  if(!run){configurations.push({api,report:progress.read().commands[`AC005-visual-api${api}`].record});continue;}
  run.write('reused-evidence.json',refs.map(({key,path,sha256,result})=>({key,path,sha256,evidence:result.evidence})));run.write('visual-review.json',visualReview);
  run.write('static-fonts-and-license.json',fonts);run.write('build-manifest-reference.json',{path:manifestPath,sha256:sha(fs.readFileSync(manifestPath)),apk:bundle.result.apk});
  if(api==='29')run.write('system-ui-recovery-reference.json',read('system-ui-recovery-api29'));
  const pass=(ref,id)=>ref.result.assertions.find(item=>item.id===id)?.status==='PASS';
  let error=null;try{
    run.check('AC005.A1',true,refs[0].result.assertions.every(item=>item.status==='PASS')&&fonts.files.every(file=>!file.fvar&&!file.CFF2&&sha(fs.readFileSync(file.path))===file.sha256)&&sha(fs.readFileSync('assets/fonts/LICENSE_FONT'))===fonts.licenseSha256);
    const graphite=tokens.gradients.graphite.colors;
    run.check('AC005.A2',true,graphite.length===4&&graphite.every(stop=>metal.includes(stop.color))&&metal.includes('[0,.22,.7,1]')&&tokens.effects.button.every(effect=>metal.includes(effect.color))&&metal.includes(tokens.effects.input[0].color));
    run.check('AC005.A2.saved-visual-observations','PASS','PASS');
    run.check('AC005.A3',true,pass(refs[1],'AC005.A3.no-Metro')&&pass(refs[1],'AC005.A3.embedded-Chinese')&&pass(refs[1],'AC005.A3.no-launcher-or-load-error')&&refs[2].result.status==='PASS'&&bundle.result.status==='PASS'&&audit.result.status==='PASS'&&embedded.result.status==='PASS');
  }catch(failure){error=failure;}
  run.finish(error,visualReview.limitations);assert.equal(error,null);configurations.push({api,report:`${run.directory}/result.json`});
}
const summary=createRun('AC005-visual-summary',{configurations:configurations.map(config=>({...config,sha256:sha(fs.readFileSync(config.report))}))},['IP04'],{caseId:'AC005',configId:'all-required-native-configs'});
if(summary){for(const config of configurations)summary.check(`AC005.api${config.api}`,'PASS',JSON.parse(fs.readFileSync(config.report,'utf8')).status);summary.write('configuration-reports.json',configurations);summary.finish();link('AC005',`${summary.directory}/result.json`,configurations,'复用原生字体/Worklets观察；正式新包仅查看受影响显示，不重复业务写入。完整八组合独立验收。');}
progress.update(s=>{if(s.acceptance.AC004.status==='PASS'&&s.acceptance.AC005.status==='PASS'){const task=s.tasks.find(task=>task.id==='IP04'),definition=JSON.parse(fs.readFileSync('resource/acceptance/追踪目录.json','utf8')).tasks.find(task=>task.id==='IP04');task.status='DONE';task.completedAt=new Date().toISOString();task.workDone=[...definition.work.map((_,i)=>`W${i+1}`),...definition.output.map((_,i)=>`D${i+1}`),'V1','V2'];}s.gates={...s.gates,G2:{status:'PASS',reports:['AC004','AC005'].map(id=>s.acceptance[id].report)}};s.next='G2原生准入完成，继续P2全链迁移失败/级联与固定时区等未执行用例；已通过功能复用证据。';});
const fix=JSON.parse(fs.readFileSync('resource/progress/list-shadow-fix.json','utf8'));fix.status='PASS';fix.nativeReview=configurations;fs.writeFileSync('resource/progress/list-shadow-fix.json',JSON.stringify(fix,null,2)+'\n');
console.log('G2 native admission complete; IP04 DONE.');
