'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),runtime=path.join(root,'.artifacts/acceptance/runtime');
function filesBelow(directory){return fs.readdirSync(directory,{withFileTypes:true}).flatMap(e=>e.isDirectory()?filesBelow(path.join(directory,e.name)):[path.join(directory,e.name)]);}
function compile(){
 const inputs=['tsconfig.ui-tests.json','pnpm-lock.yaml',...filesBelow(path.join(root,'tests/ui')).filter(f=>f.endsWith('.ts')),...filesBelow(path.join(root,'src')).filter(f=>/\.tsx?$/.test(f))].map(f=>path.resolve(root,f)).sort();
 const fingerprint=crypto.createHash('sha256').update(inputs.map(f=>path.relative(root,f)+'\0'+crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')).join('\n')).digest('hex'),marker=path.join(runtime,'compiled-inputs.json');
 if(fs.existsSync(marker)&&JSON.parse(fs.readFileSync(marker)).sha256===fingerprint&&fs.existsSync(path.join(runtime,'tests/ui/evidence.test.js')))return {runtime,cached:true,sha256:fingerprint};
 const result=spawnSync(process.execPath,[require.resolve('typescript/bin/tsc'),'-p','tsconfig.ui-tests.json'],{cwd:root,encoding:'utf8',windowsHide:true,maxBuffer:8*1024*1024});assert.equal(result.status,0,result.stdout+result.stderr);fs.writeFileSync(marker,JSON.stringify({sha256:fingerprint})+'\n');return {runtime,cached:false,sha256:fingerprint};
}
module.exports={compile,root,runtime,filesBelow};
if(require.main===module)console.log(JSON.stringify(compile()));
