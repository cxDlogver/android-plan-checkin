const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process'),{createHash}=require('node:crypto');
const {env,toolRoot}=require('./task-env.cjs'),progress=require('./progress.cjs');
const variant=process.argv[2]||'debug';if(!['debug','release'].includes(variant))throw new Error('debug or release required');
const state=progress.read(),build=state.commands[`native-${variant}`];if(build?.status!=='PASS')throw new Error('A successful native build is required.');
const apk=build.artifacts.find(file=>file.path.endsWith('.apk')),sha=bytes=>createHash('sha256').update(bytes).digest('hex');
if(!apk||sha(fs.readFileSync(apk.path))!==apk.sha256)throw new Error('APK hash does not match build evidence.');
const directory=`resource/acceptance/runs/${new Date().toISOString().replace(/[:.]/g,'-')}/apk-audit-${variant}`;fs.mkdirSync(directory,{recursive:true});
const tools=path.join(toolRoot,'sdk/build-tools/35.0.0');
const previous=state.commands[`apk-audit-${variant}`];
const reuse=previous?.apk?.sha256===apk.sha256&&previous.evidence?.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256);
function readOrExecute(name,execute){const saved=reuse&&previous.evidence.find(file=>file.path.endsWith(`/${name}`));const content=saved?fs.readFileSync(saved.path,'utf8'):execute();fs.writeFileSync(`${directory}/${name}`,content);return content;}
function aapt(args){return execFileSync(path.join(tools,'aapt2.exe'),args,{env,encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024});}
const badging=readOrExecute('badging.log',()=>aapt(['dump','badging',apk.path]));
const manifest=readOrExecute('manifest.log',()=>aapt(['dump','xmltree',apk.path,'--file','AndroidManifest.xml']));
const resources=readOrExecute('xml-resource-paths.log',()=>aapt(['dump','resources',apk.path]).split(/\r?\n/).flatMap((line,index,lines)=>/resource 0x[0-9a-f]+ xml\//.test(line)?[line,lines[index+1]]:[]).join('\n'));
function resourceFile(name){const escaped=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const match=resources.match(new RegExp(`resource (0x[0-9a-f]+) xml/${escaped}\\s+\\(\\) \\(file\\) (\\S+)`));if(!match)throw new Error(`Missing XML resource: ${name}`);const attribute=name==='backup_rules'?'fullBackupContent':'dataExtractionRules';if(!new RegExp(`android:${attribute}[^\\n]*@${match[1]}`).test(manifest))throw new Error(`${attribute} does not reference ${name}`);return match[2];}
const backup=readOrExecute('backup-rules.log',()=>aapt(['dump','xmltree',apk.path,'--file',resourceFile('backup_rules')]));
const extraction=readOrExecute('data-extraction-rules.log',()=>aapt(['dump','xmltree',apk.path,'--file',resourceFile('data_extraction_rules')]));
const signature=readOrExecute('signature.log',()=>execFileSync('cmd.exe',['/d','/s','/c',`${path.join(tools,'apksigner.bat')} verify --verbose --print-certs ${path.resolve(apk.path)}`],{env,encoding:'utf8',windowsHide:true,maxBuffer:1024*1024}));
const assertions=[];
function check(id,expected,actual){assertions.push({id,expected,actual,status:JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL'});}
const identity=badging.match(/package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'/);
check('package',variant==='release'?'com.xiang.plancheckin':'com.xiang.plancheckin.dev',identity?.[1]);
check('minSdk',29,Number(badging.match(/(?:minSdkVersion|sdkVersion):'(\d+)'/)?.[1]));check('targetSdk',36,Number(badging.match(/targetSdkVersion:'(\d+)'/)?.[1]));
const compiled=manifest.match(/android:compileSdkVersion[^\n]*\(type 0x10\)0x([0-9a-f]+)/i);
check('compileSdk',36,compiled?parseInt(compiled[1],16):Number(manifest.match(/android:compileSdkVersion[^\n]*=(\d+)/)?.[1]));
check('allowBackup',false,!/android:allowBackup[^\n]*=false/.test(manifest)&&!/android:allowBackup[^\n]*(?:0x0\b|0x00000000\b)/.test(manifest));
const domains=['root','file','database','sharedpref','external','device_root','device_file','device_database','device_sharedpref'];
const cloudStart=extraction.indexOf('E: cloud-backup'),transferStart=extraction.indexOf('E: device-transfer');
for(const [name,content] of [['backup',backup],['cloud',extraction.slice(cloudStart,transferStart)],['transfer',extraction.slice(transferStart)]])check(`${name}.domains`,domains,domains.filter(domain=>new RegExp(`domain[^\n]*="${domain}"`).test(content)));
check('extractionSections',true,extraction.includes('cloud-backup')&&extraction.includes('device-transfer'));
check('excludedPermissions',[],[...badging.matchAll(/uses-permission: name='([^']+)'/g)].map(match=>match[1]).filter(permission=>/POST_NOTIFICATIONS|ACCESS_(?:COARSE|FINE)_LOCATION|CAMERA|RECORD_AUDIO|READ_MEDIA|READ_EXTERNAL_STORAGE|WRITE_EXTERNAL_STORAGE/.test(permission)));
check('signatureVerified',true,/Verifies/.test(signature));
if(variant==='release'){
  check('debuggable',false,badging.includes('application-debuggable'));
  const signing=JSON.parse(fs.readFileSync('resource/progress/release-signing.json','utf8').replace(/^\uFEFF/,''));
  check('longTermCertificate',signing.certificateSha256,signature.match(/Signer #1 certificate SHA-256 digest: ([a-fA-F0-9]+)/)?.[1].toLowerCase());
}
const status=assertions.every(item=>item.status==='PASS')?'PASS':'FAIL';
const result={status,variant,recordedAt:new Date().toISOString(),buildRecord:build.record,previousRecord:previous?.record||null,reusedRawEvidence:!!reuse,apk,identity:{package:identity?.[1],versionCode:Number(identity?.[2]),versionName:identity?.[3]},assertions,evidence:['badging.log','manifest.log','xml-resource-paths.log','backup-rules.log','data-extraction-rules.log','signature.log'].map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))};
fs.writeFileSync(`${directory}/assertions.json`,JSON.stringify(assertions,null,2)+'\n');fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
fs.writeFileSync(`${directory}/evidence-manifest.json`,JSON.stringify([...result.evidence,...['assertions.json','result.json'].map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))],null,2)+'\n');
progress.update(s=>{s.commands[`apk-audit-${variant}`]={...result,record:`${directory}/result.json`};s.tasks.find(task=>task.id==='IP03').evidence.push(`${directory}/result.json`);});
console.log(`${status}: ${directory}/result.json`);if(status!=='PASS'){console.log(JSON.stringify(assertions.filter(item=>item.status==='FAIL')));process.exitCode=1;}
