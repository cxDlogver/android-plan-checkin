'use strict';
// Scoped to the project Appium process via --require; installed dependencies stay untouched.
if(process.platform==='win32'){
 const childProcess=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
 const report=path.resolve(__dirname,'../evidence/preparation/services/appium-hidden-processes.jsonl');
 let observations=0;
 for(const method of ['spawn','spawnSync']){
  const original=childProcess[method];
  childProcess[method]=function(command,args,options){
   if(!Array.isArray(args)){options=args;args=[];}
   const actual={...options,windowsHide:true};
   if(observations<10){fs.mkdirSync(path.dirname(report),{recursive:true});fs.appendFileSync(report,JSON.stringify({at:new Date().toISOString(),parentPid:process.pid,method,executable:path.basename(String(command)),windowsHide:actual.windowsHide})+'\n');observations++;}
   return original.call(this,command,args,actual);
  };
 }
 require('node:module').syncBuiltinESMExports();
}
