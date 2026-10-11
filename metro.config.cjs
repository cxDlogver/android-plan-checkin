const { getDefaultConfig } = require('expo/metro-config');
const path=require('node:path');
const config=getDefaultConfig(__dirname);
// Evidence and tool builds grow during device validation; none are application modules.
const excluded=['.git','.expo','.cache','.artifacts','android','resource','scripts','tests'];
const root=__dirname.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
config.resolver.blockList=[...(Array.isArray(config.resolver.blockList)?config.resolver.blockList:config.resolver.blockList?[config.resolver.blockList]:[]),...excluded.map(directory=>new RegExp(`${root}[\\\\/]${directory.replace('.','\\.')}(?:[\\\\/].*)?$`))];
config.resolver.resolveRequest=(context,moduleName,platform)=>{
  const development=process.env.APP_VARIANT==='development';
  if(moduleName==='@verification')return {type:'sourceFile',filePath:path.join(__dirname,'src/verification',development?'development.tsx':'production.tsx')};
  if(moduleName==='@verification/runtime')return {type:'sourceFile',filePath:path.join(__dirname,'src/verification',development?'runtime-development.ts':'runtime-production.ts')};
  return context.resolveRequest(context,moduleName,platform);
};
module.exports=config;
