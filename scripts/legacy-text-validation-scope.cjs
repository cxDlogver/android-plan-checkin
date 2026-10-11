const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process'),{sha}=require('./p1.cjs');
module.exports=function(record){const files=JSON.parse(fs.readFileSync(path.join(path.dirname(record),'source-snapshot.json'),'utf8')),commit='e48c6e5ff949569b10e15875ace8c73cd179e189',old=execFileSync('git',['show',commit+':src/domain/commands.ts'],{encoding:'utf8',windowsHide:true}),current=fs.readFileSync('src/domain/commands.ts','utf8');
 const core=text=>text.slice(text.indexOf('const id='),text.indexOf('export function canonical'));
 const dependencies=files.filter(s=>s.path==='src/domain/model.ts'||s.path==='tests/domain/bdd-validation.test.ts').map(s=>({...s,currentSha256:sha(fs.readFileSync(s.path))}));
 return {commit,expectedOldFileSha256:files.find(s=>s.path==='src/domain/commands.ts').sha256,oldFileSha256:sha(old),originalValidationSha256:sha(core(old)),currentValidationSha256:sha(core(current)),dependencies,scope:'All Zod text, name, note, Create/Edit/record schemas and normalizeEnvelope are byte-identical. The later applyCommand cross-day guard and imported rule calculation functions are not called by these pure normalization tests.'};
};
