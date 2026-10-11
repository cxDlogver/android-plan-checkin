const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const {apkZip}=require('./apk-zip.cjs'),progress=require('./progress.cjs');
const sha=value=>createHash('sha256').update(value).digest('hex'),state=progress.read(),build=state.commands['native-release'];assert.equal(build.status,'PASS');
const apk=build.artifacts[0];assert.equal(sha(fs.readFileSync(apk.path)),apk.sha256);
const frozenPath=path.dirname(build.record)+'/bundle-source-snapshot.json',frozen=JSON.parse(fs.readFileSync(frozenPath,'utf8'));
const mapPath='android/app/build/generated/sourcemaps/react/release/index.android.bundle.map',map=JSON.parse(fs.readFileSync(mapPath,'utf8')),zip=apkZip(apk.path),bundle=zip.read('assets/index.android.bundle');
const directory=`resource/acceptance/runs/${new Date().toISOString().replace(/[:.]/g,'-')}/apk-bundle-audit`;fs.mkdirSync(directory,{recursive:true});
const assertions=[];function check(id,expected,actual){const status=JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL';assertions.push({id,expected,actual,status});}
const projectSources=map.sources.flatMap((source,index)=>/^\/(app|src)\//.test(source)?[{path:source.slice(1),sha256:sha(map.sourcesContent[index]||'')}]:[]);
for(const item of projectSources)check(`frozen-source:${item.path}`,frozen.files.find(file=>file.path===item.path)?.sha256,item.sha256);
check('production-verification-entries',[],projectSources.filter(item=>item.path.startsWith('src/verification/')&&!['src/verification/production.tsx','src/verification/runtime-production.ts'].includes(item.path)).map(item=>item.path));
check('production-clock',true,projectSources.some(item=>item.path==='src/verification/runtime-production.ts'));
check('hermes-bytecode', 'c61fbc03c103191f',bundle.subarray(0,8).toString('hex'));
const fonts=frozen.files.filter(file=>file.path.endsWith('.ttf'));
const fontEntries=zip.entries.filter(entry=>entry.size>1000000&&entry.name!=='assets/index.android.bundle'&&!entry.name.startsWith('lib/')).map(entry=>({name:entry.name,sha256:sha(zip.read(entry.name)),bytes:entry.size}));
const embeddedFonts=fonts.map(font=>({...font,apkEntries:fontEntries.filter(entry=>entry.sha256===font.sha256).map(entry=>entry.name)}));for(const font of embeddedFonts)check(`embedded-font:${font.path}`,1,font.apkEntries.length);
const sentinels=['plancheckin-v2:','native.fixture.load','native.fault.beforeCommit','原生模块验证','next COMMIT','verificationExecutor','plancheckin-verification','CLOSE_ISOLATED_DEV_CONNECTION'];for(const text of sentinels)check(`excluded-sentinel:${text}`,false,bundle.includes(Buffer.from(text)));
const config=JSON.parse(zip.read('assets/app.config').toString('utf8'));check('native-config-package','com.xiang.plancheckin',config.android.package);check('native-config-version',state.commands['apk-audit-release'].identity.versionName,config.version);
const status=assertions.every(item=>item.status==='PASS')?'PASS':'FAIL';
const manifest={schemaVersion:1,status,recordedAt:new Date().toISOString(),apk,buildRecord:build.record,apkAuditRecord:state.commands['apk-audit-release'].record,certificateSha256:JSON.parse(fs.readFileSync('resource/progress/release-signing.json','utf8').replace(/^\uFEFF/,'')).certificateSha256,identity:state.commands['apk-audit-release'].identity,frozenSource:{path:frozenPath,sha256:sha(fs.readFileSync(frozenPath)),sourceSha256:frozen.sourceSha256},hermesBundle:{apkEntry:'assets/index.android.bundle',sha256:sha(bundle),bytes:bundle.length},embeddedFonts,projectSources,sourceMap:{path:mapPath,sha256:sha(fs.readFileSync(mapPath))},assertions,evidence:[frozenPath].map(file=>({path:file,sha256:sha(fs.readFileSync(file))}))};
const manifestPath=`${directory}/build-manifest.json`;
fs.writeFileSync(`${directory}/assertions.json`,JSON.stringify(assertions,null,2)+'\n');fs.writeFileSync(`${directory}/result.json`,JSON.stringify(manifest,null,2)+'\n');fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync('resource/progress/current-build.json',JSON.stringify({manifestPath,apkSha256:apk.sha256},null,2)+'\n');
fs.writeFileSync(`${directory}/evidence-manifest.json`,JSON.stringify([...manifest.evidence,...['assertions.json','result.json'].map(name=>({path:`${directory}/${name}`,sha256:sha(fs.readFileSync(`${directory}/${name}`))}))],null,2)+'\n');
progress.update(s=>{s.commands['apk-bundle-audit']={status,record:`${directory}/result.json`,manifestPath};s.tasks.find(task=>task.id==='IP03').evidence.push(`${directory}/result.json`);});console.log(`${status}: ${directory}/result.json`);if(status!=='PASS'){console.log(JSON.stringify(assertions.filter(item=>item.status==='FAIL')));process.exitCode=1;}
