const fs=require('node:fs');
const {getConfig}=require('expo/config');
const checks=[];
const original={variant:process.env.APP_VARIANT,code:process.env.PLANCHECKIN_VERSION_CODE,name:process.env.PLANCHECKIN_VERSION_NAME};
function read(variant,code,name){process.env.APP_VARIANT=variant;process.env.PLANCHECKIN_VERSION_CODE=code;process.env.PLANCHECKIN_VERSION_NAME=name;return getConfig(process.cwd(),{skipSDKVersionRequirement:true}).exp;}
try{
  for(const [variant,code,name,expectedPackage] of [['production','1','1.0.0','com.xiang.plancheckin'],['production','2','1.0.1','com.xiang.plancheckin'],['development','2','1.0.1','com.xiang.plancheckin.dev']]){
    const config=read(variant,code,name),expected={package:expectedPackage,versionCode:Number(code),version:name},actual={package:config.android.package,versionCode:config.android.versionCode,version:config.version};checks.push({expected,actual,status:JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL'});
  }
  for(const code of ['0','-1','2.5','2100000001','NaN']){let rejected=false;try{read('production',code,'1.0.0');}catch{rejected=true;}checks.push({input:{versionCode:code},expected:'rejected',actual:rejected?'rejected':'accepted',status:rejected?'PASS':'FAIL'});}
  let rejected=false;try{read('production','1','invalid');}catch{rejected=true;}checks.push({input:{versionName:'invalid'},expected:'rejected',actual:rejected?'rejected':'accepted',status:rejected?'PASS':'FAIL'});
}finally{
  for(const [key,value] of Object.entries({APP_VARIANT:original.variant,PLANCHECKIN_VERSION_CODE:original.code,PLANCHECKIN_VERSION_NAME:original.name}))if(value===undefined)delete process.env[key];else process.env[key]=value;
}
const status=checks.every(check=>check.status==='PASS')?'PASS':'FAIL';fs.writeFileSync('resource/progress/config-version-check.json',JSON.stringify({status,recordedAt:new Date().toISOString(),scope:'new build version inputs only',checks},null,2)+'\n');console.log(`${status}: ${checks.length} version-input checks`);if(status!=='PASS')process.exitCode=1;
