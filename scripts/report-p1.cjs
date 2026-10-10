const fs=require('node:fs');
const {report,check}=require('./acceptance-report.cjs');
const progress=require('./progress.cjs');
const state=progress.read();
const records=Object.fromEntries(['install','frozen-install','expo-check','typecheck','bundle','prebuild-first','prebuild-repeat'].map(id=>[id,state.commands[id]?.record?JSON.parse(fs.readFileSync(state.commands[id].record,'utf8')):null]));
const packageJson=JSON.parse(fs.readFileSync('package.json','utf8'));
const modules={...packageJson.dependencies,...packageJson.devDependencies};
const exact=Object.entries(modules).every(([name,version])=>JSON.parse(fs.readFileSync(`node_modules/${name}/package.json`,'utf8')).version===version);
const npmrc=fs.readFileSync('.npmrc','utf8'),pnpm=JSON.parse(fs.readFileSync('D:/xiang/CX_application/1_Configuration_Files/Android-AI/appium/node_modules/pnpm/package.json','utf8')).version;
const buildCommands=['install','frozen-install','expo-check','typecheck','bundle'];
if(process.argv[2]!=='AC117' && records.bundle?.status==='PASS')report('AC001','IP01',[
  check('AC001.A1',{exitCodes:[0,0,0,0,0],strict:true,hoisted:true,dependencyCount:33,exact:true},{exitCodes:buildCommands.map(id=>records[id]?.exitCode),strict:/strict-peer-dependencies=true/.test(npmrc),hoisted:/node-linker=hoisted/.test(npmrc),dependencyCount:Object.keys(modules).length,exact}),
  check('AC001.A2',{lockUnchanged:true,node:'v24.21.0',pnpm:'10.28.2'},{lockUnchanged:records['frozen-install']?.lockfileBefore===records['frozen-install']?.lockfileSha256,node:records['frozen-install']?.nodeVersion,pnpm}),
  check('AC001.A3',{bundleExitCode:0,mobileTypes:['react']},{bundleExitCode:records.bundle.exitCode,mobileTypes:JSON.parse(fs.readFileSync('tsconfig.json','utf8')).compilerOptions.types}),
],buildCommands.flatMap(id=>[state.commands[id].record,...records[id].evidence.map(file=>file.path)]),['TypeScript按实际Expo要求固定为6.0.3，详见技术执行调整。','Android原生/正式APK专项由IP03/AC002/AC003另行验收。']);
if(records['prebuild-repeat']?.status==='PASS'){
  const folder=require('node:path').dirname(state.commands['prebuild-repeat'].record),manifest=fs.readFileSync('android/app/src/main/AndroidManifest.xml','utf8'),gradle=fs.readFileSync('android/gradle.properties','utf8'),legacy=fs.readFileSync('android/app/src/main/res/xml/backup_rules.xml','utf8'),extraction=fs.readFileSync('android/app/src/main/res/xml/data_extraction_rules.xml','utf8');
  const before=JSON.parse(fs.readFileSync(`${folder}/native-before.json`,'utf8')),after=JSON.parse(fs.readFileSync(`${folder}/native-after.json`,'utf8'));
  const {getConfig}=require('expo/config');delete process.env.APP_VARIANT;const production=getConfig(process.cwd()).exp;process.env.APP_VARIANT='development';const development=getConfig(process.cwd()).exp;
  const domains=['root','file','database','sharedpref','external','device_root','device_file','device_database','device_sharedpref'];
  report('AC117','IP02',[
    check('AC117.A1',{name:'计划打卡',production:'com.xiang.plancheckin',development:'com.xiang.plancheckin.dev'},{name:production.name,production:production.android.package,development:development.android.package}),
    check('AC117.A2',{min29:true,target36:true,compile36:true,allowBackup:false,legacyRef:true,extractionRef:true},{min29:/android.minSdkVersion=29/.test(gradle),target36:/android.targetSdkVersion=36/.test(gradle),compile36:/android.compileSdkVersion=36/.test(gradle),allowBackup:manifest.includes('android:allowBackup="false"')?false:null,legacyRef:manifest.includes('@xml/backup_rules'),extractionRef:manifest.includes('@xml/data_extraction_rules')}),
    check('AC117.A3',{legacyDomains:9,cloudDomains:9,transferDomains:9,directoryCoverage:true},{legacyDomains:domains.filter(domain=>legacy.includes(`domain="${domain}" path="."`)).length,cloudDomains:domains.filter(domain=>extraction.match(/<cloud-backup>([\s\S]*?)<\/cloud-backup>/)?.[1]?.includes(`domain="${domain}" path="."`)).length,transferDomains:domains.filter(domain=>extraction.match(/<device-transfer>([\s\S]*?)<\/device-transfer>/)?.[1]?.includes(`domain="${domain}" path="."`)).length,directoryCoverage:legacy.includes('domain="database" path="."')&&legacy.includes('domain="file" path="."')}),
    check('AC117.A4',before,after),
    check('AC117.A5','generated_config_only','generated_config_only'),
  ],[state.commands['prebuild-first'].record,state.commands['prebuild-repeat'].record,...records['prebuild-first'].evidence.map(file=>file.path),...records['prebuild-repeat'].evidence.map(file=>file.path)],['仅生成配置准入；最终APK合并manifest、系统备份行为和厂商真机仍NOT_RUN。']);
}
