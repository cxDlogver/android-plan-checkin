const {spawnSync}=require('node:child_process');
const {env}=require('./task-env.cjs');
const action=process.argv[2]||'probe';
const gitEnv={...env,GIT_SSH_COMMAND:'ssh -o BatchMode=yes'};
function git(args,options={}){const r=spawnSync('git',args,{env:gitEnv,encoding:'utf8',windowsHide:true,timeout:60000,...options});console.log(JSON.stringify({args,exitCode:r.status,stdout:r.stdout,stderr:r.stderr,error:r.error?.message}));if(r.status!==0)process.exitCode=1;return r;}
if(action==='probe')git(['ls-remote','origin']);
else if(action==='commit'){
  const message=process.argv[3]||'Start P1 engineering baseline and evidence tracking';
  const identity=spawnSync('git',['config','user.name'],{env:gitEnv,encoding:'utf8'});
  if(!identity.stdout.trim())git(['config','user.name','cxDlogver']);
  const email=spawnSync('git',['config','user.email'],{env:gitEnv,encoding:'utf8'});
  if(!email.stdout.trim())git(['config','user.email','97222936+cxDlogver@users.noreply.github.com']);
  if(git(['add','.']).status===0)git(['commit','-m',message]);
}else if(action==='push')git(['push','-u','origin','main']);
else throw new Error('Expected probe, commit or push');
