const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{createHash}=require('node:crypto'),{apkZip}=require('./apk-zip.cjs');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function validateNativeReuse(recordPath,sources,directory){
  const prior=JSON.parse(fs.readFileSync(recordPath,'utf8'));assert.equal(prior.status,'PASS');assert.equal(prior.action,'release');
  const priorSource=JSON.parse(fs.readFileSync(prior.sourceSnapshot,'utf8'));
  const native=file=>/^(android\/|plugins\/|package.json$|pnpm-lock.yaml$)/.test(file.path);
  const before=priorSource.sources.filter(native),after=sources.filter(native);assert.deepEqual(after,before,'Native input changed: a full native build is required.');
  const artifact=prior.artifacts[0],stable=`.artifacts/apk/release/${artifact.sha256.slice(0,16)}.apk`,apk=fs.existsSync(stable)?stable:artifact.path;assert.equal(sha(fs.readFileSync(apk)),artifact.sha256);
  const zip=apkZip(apk),libraries=zip.entries.filter(entry=>entry.name.startsWith('lib/')&&entry.name.endsWith('.so')).map(entry=>{const output=`android/app/build/intermediates/stripped_native_libs/release/stripReleaseDebugSymbols/out/${entry.name}`;assert.ok(fs.existsSync(output),`Cached native output missing: ${output}`);const expected=sha(zip.read(entry.name)),actual=sha(fs.readFileSync(output));assert.equal(actual,expected,`Cached native output changed: ${output}`);return {apkEntry:entry.name,path:output,sha256:actual};});assert.ok(libraries.length>0);
  const log=fs.readFileSync(prior.log,'utf8'),excludedTasks=[...new Set([...log.matchAll(/^> Task (\S*(?:buildCMakeRelWithDebInfo|configureCMakeRelWithDebInfo|externalNativeBuildRelease|generateJsonModelRelease)\S*)/gm)].map(match=>match[1]))];assert.ok(excludedTasks.length>0);
  const report={status:'PASS',recordedAt:new Date().toISOString(),scope:'reuse identical native inputs and stripped libraries from an already successful signed release; JS bundle is rebuilt',priorBuild:recordPath,priorApkSha256:artifact.sha256,nativeInputSha256:sha(JSON.stringify(after)),libraries,excludedTasks};fs.writeFileSync(`${directory}/native-reuse.json`,JSON.stringify(report,null,2)+'\n');return excludedTasks;
}
module.exports={validateNativeReuse};
