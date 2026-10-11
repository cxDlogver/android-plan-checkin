const fs=require('node:fs'),assert=require('node:assert/strict'),{sha}=require('./p1.cjs'),progress=require('./progress.cjs');
const command=progress.read().commands['apk-bundle-audit'],manifestPath=command.manifestPath||'resource/progress/build-manifest.json';
const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8')),source=manifest.sourceMap.path;
const target=`.artifacts/apk/release/${manifest.apk.sha256.slice(0,16)}.map`;
if(fs.existsSync(target))assert.equal(sha(fs.readFileSync(target)),manifest.sourceMap.sha256);
else{assert.equal(sha(fs.readFileSync(source)),manifest.sourceMap.sha256);fs.copyFileSync(source,target);}
manifest.sourceMap={...manifest.sourceMap,path:target,generatedFrom:manifest.sourceMap.generatedFrom||source};
fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');console.log('Preserved the exact compiler source map beside the immutable APK.');
