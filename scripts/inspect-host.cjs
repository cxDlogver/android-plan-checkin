const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const { toolRoot, nodeRoot, env, node, javaRoot } = require('./task-env.cjs');
const files = ['pnpm','sdk/ndk','sdk/cmake','logs/runtime-state.json'].map(p => [p, fs.existsSync(`${toolRoot}/${p}`) ? (fs.statSync(`${toolRoot}/${p}`).isDirectory() ? fs.readdirSync(`${toolRoot}/${p}`) : JSON.parse(fs.readFileSync(`${toolRoot}/${p}`,'utf8'))) : null]);
const versions = [ [node, ['--version']], [`${javaRoot}/bin/java.exe`, ['-version']] ].map(([command,args]) => { const r=spawnSync(command,args,{env,encoding:'utf8'}); return {command,exitCode:r.status,stdout:r.stdout,stderr:r.stderr,error:r.error?.message}; });
const inherited = ['F:/AGENTS.md','F:/CX_notes/AGENTS.md','F:/CX_notes/cx-learn-notes/AGENTS.md'].filter(p=>fs.existsSync(p)).map(p=>({path:p,text:fs.readFileSync(p,'utf8')}));
const credential = spawnSync('git',['credential','fill'],{env,encoding:'utf8',input:'protocol=https\nhost=github.com\n\n',timeout:15000});
const credentialFields = Object.fromEntries((credential.stdout||'').trim().split('\n').map(line=>{const i=line.indexOf('=');return [line.slice(0,i),line.slice(i+1)];}));
console.log(JSON.stringify({nodeRoot,files,versions,inherited,credentials:{exitCode:credential.status,username:credentialFields.username||null,available:!!credentialFields.password},gitEnvironment:Object.keys(process.env).filter(k=>k.startsWith('GIT_')).map(k=>({key:k,value:/TOKEN|PASSWORD|SECRET|KEY/.test(k)?'[redacted]':process.env[k]}))},null,2));
