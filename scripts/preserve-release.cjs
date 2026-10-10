const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{createHash}=require('node:crypto'),progress=require('./progress.cjs');
const state=progress.read(),build=state.commands['native-release'];assert.equal(build.status,'PASS');const apk=build.artifacts.find(item=>item.path.endsWith('.apk'));
const sha=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');assert.equal(sha(apk.path),apk.sha256);
const target=`.artifacts/apk/release/${apk.sha256.slice(0,16)}.apk`;fs.mkdirSync(path.dirname(target),{recursive:true});if(!fs.existsSync(target))fs.copyFileSync(apk.path,target);assert.equal(sha(target),apk.sha256);
const directory=`resource/acceptance/runs/${new Date().toISOString().replace(/[:.]/g,'-')}/release-preservation`;fs.mkdirSync(directory,{recursive:true});
const artifact={...apk,path:target,originalPath:apk.originalPath||apk.path};const result={status:'PASS',recordedAt:new Date().toISOString(),buildRecord:build.record,artifact};fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
progress.update(s=>{s.commands['native-release'].artifacts=[artifact];s.commands['release-preservation']={status:'PASS',record:`${directory}/result.json`};});console.log(target);
