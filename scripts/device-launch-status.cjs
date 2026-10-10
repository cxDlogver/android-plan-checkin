const fs=require('node:fs'),path=require('node:path'),{toolRoot}=require('./task-env.cjs');
for(const name of ['appium-4723.log','emulator-api36.stdout.log','emulator-api36.stderr.log']){
  const file=path.join(toolRoot,'logs',name);if(!fs.existsSync(file)){console.log(`${name}: absent`);continue;}
  const stat=fs.statSync(file);console.log(JSON.stringify({name,modifiedAt:stat.mtime.toISOString(),bytes:stat.size,tail:fs.readFileSync(file,'utf8').split(/\r?\n/).filter(Boolean).slice(-5).map(line=>line.slice(0,500))}));
}
fetch('http://127.0.0.1:4723/status',{signal:AbortSignal.timeout(3000)}).then(response=>response.json()).then(result=>console.log(JSON.stringify({appium:result.value}))).catch(error=>console.log(`Appium unavailable: ${error.message}`));
