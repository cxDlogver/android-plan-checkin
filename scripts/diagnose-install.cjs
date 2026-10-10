const {spawnSync}=require('node:child_process');
const fs=require('node:fs');
const {env}=require('./task-env.cjs');
const proxyEnv=Object.fromEntries(Object.entries(process.env).filter(([key])=>/proxy/i.test(key)).map(([key,value])=>{try{return [key,new URL(value).host];}catch{return [key,'configured'];}}));
const proxy=spawnSync('reg',['query','HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings','/v','ProxyServer'],{encoding:'utf8',windowsHide:true});
const enabled=spawnSync('reg',['query','HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings','/v','ProxyEnable'],{encoding:'utf8',windowsHide:true});
console.log(JSON.stringify({proxyEnv,systemProxy:proxy.stdout,systemProxyEnabled:enabled.stdout,installedPackages:fs.existsSync('node_modules')?fs.readdirSync('node_modules').length:0},null,2));
Promise.allSettled(['https://registry.npmjs.org/expo-modules-core/-/expo-modules-core-57.0.21.tgz','https://registry.npmmirror.com/expo-modules-core/-/expo-modules-core-57.0.21.tgz'].map(async url=>{const started=Date.now();try{const r=await fetch(url,{method:'HEAD',signal:AbortSignal.timeout(8000)});console.log(JSON.stringify({url,status:r.status,elapsedMs:Date.now()-started}));}catch(error){console.log(JSON.stringify({url,error:error.message,elapsedMs:Date.now()-started}));}}));
