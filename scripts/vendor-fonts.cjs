const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const crypto=require('node:crypto');
const spec=JSON.parse(fs.readFileSync('resource/review/字体资源核查.json','utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
(async()=>{
  const existing=spec.files.every(file=>fs.existsSync(`assets/fonts/${path.basename(file.path)}`)&&sha(fs.readFileSync(`assets/fonts/${path.basename(file.path)}`))===file.sha256);
  if(existing&&fs.existsSync('assets/fonts/LICENSE_FONT')){console.log('SKIP fonts: 三份静态字体摘要与已核查来源一致');return;}
  fs.mkdirSync('.cache/font-package',{recursive:true});
  const archive='.cache/font-package/fonts.tgz';
  if(!fs.existsSync(archive)||sha(fs.readFileSync(archive))!==spec.archiveSha256){const response=await fetch(spec.source,{signal:AbortSignal.timeout(300000)});if(!response.ok)throw new Error(`Font HTTP ${response.status}`);const bytes=Buffer.from(await response.arrayBuffer());if(sha(bytes)!==spec.archiveSha256)throw new Error('字体发布包摘要与已核查来源不符');fs.writeFileSync(archive,bytes);}
  const selected=[...spec.files.map(file=>`package/${file.path}`),'package/LICENSE_FONT'];
  const extracted=spawnSync('tar',['-xzf',archive,'-C','.cache/font-package',...selected],{encoding:'utf8',windowsHide:true});
  if(extracted.status!==0)throw new Error(extracted.stderr);
  const files=[];
  for(const file of spec.files){const bytes=fs.readFileSync(`.cache/font-package/package/${file.path}`);if(sha(bytes)!==file.sha256)throw new Error('静态字体摘要不一致');const target=`assets/fonts/${path.basename(file.path)}`;fs.writeFileSync(target,bytes);files.push({...file,path:target});}
  const license=fs.readFileSync('.cache/font-package/package/LICENSE_FONT');if(sha(license)!==spec.fontLicense.sha256)throw new Error('字体许可摘要不一致');fs.writeFileSync('assets/fonts/LICENSE_FONT',license);
  fs.writeFileSync('resource/progress/font-vendoring.json',JSON.stringify({status:'PASS',scope:'local_vendoring_only',source:spec.source,archiveSha256:spec.archiveSha256,files,licenseSha256:sha(license),androidLoading:'NOT_RUN'},null,2)+'\n');console.log('PASS 三份静态字体及OFL已嵌入；原生加载仍需另验');
})().catch(error=>{console.error(error.message);process.exitCode=1;});
