const fs=require('node:fs'),path=require('node:path'),{snapshot,sha}=require('./p1.cjs'),progress=require('./progress.cjs');
function files(folder){return fs.readdirSync(folder,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(path.join(folder,e.name)):path.join(folder,e.name));}
const metadata=JSON.parse(fs.readFileSync('.artifacts/bundle/metadata.json','utf8'));
const all=files('.artifacts/bundle');
const bundles=all.filter(file=>/\.(js|hbc)$/.test(file));
if(!bundles.length)throw new Error('No Android bundle output');
const dev=fs.readFileSync('src/verification/development.tsx','utf8');
const testIds=[...dev.matchAll(/testID="([^"]+)"/g)].map(match=>match[1]);
if(!testIds.length)throw new Error('Missing development sample sentinel');
const devSentinels=[...testIds,'development before-commit fault','development lost commit acknowledgement','隔离开发验收夹具','性能夹具'].map(value=>({value,present:bundles.some(file=>fs.readFileSync(file).includes(Buffer.from(value)))}));
const status=devSentinels.every(row=>!row.present)?'PASS':'FAIL';
const result={status,scope:'Android production JS bundle; native manifest/permissions/offline runtime NOT_RUN',recordedAt:new Date().toISOString(),metadata,devSentinels,files:snapshot(all),sourceRevision:progress.read().commands.bundle.inputSha256};
fs.writeFileSync('resource/progress/bundle-audit.json',JSON.stringify(result,null,2)+'\n');
progress.update(s=>{s.commands['bundle-audit']={status,record:'resource/progress/bundle-audit.json',inputSha256:sha(JSON.stringify(result.files))};});
console.log(`${status}: development sentinels excluded; ${all.length} bundle assets hashed`);if(status!=='PASS')process.exitCode=1;
