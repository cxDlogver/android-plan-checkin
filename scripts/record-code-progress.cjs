const fs=require('node:fs');
const {snapshot,sha}=require('./p1.cjs');
const progress=require('./progress.cjs');
const files=snapshot(['app','src','plugins','assets','tests','package.json','pnpm-lock.yaml','app.config.ts','tsconfig.json','tsconfig.node.json','tsconfig.integration.json','metro.config.cjs','babel.config.cjs']);
const artifact='resource/progress/implementation-snapshot.json';
fs.writeFileSync(artifact,JSON.stringify({schemaVersion:1,status:'CODE_WRITTEN',recordedAt:new Date().toISOString(),sourceSha256:sha(JSON.stringify(files)),files,limitations:['源码存在不代表原生或BDD场景通过；退出条件继续独立跟踪。']},null,2)+'\n');
progress.update(state=>{
  for(const task of state.tasks.filter(task=>Number(task.id.slice(2))>=3&&Number(task.id.slice(2))<=25)){if(task.status==='NOT_STARTED')task.status='IN_PROGRESS';task.startedAt??=new Date().toISOString();task.implementationStatus='CODE_WRITTEN';if(!task.evidence.includes(artifact))task.evidence.push(artifact);}
});
console.log('领域、应用服务、页面与路由的源码快照和进度已写入。');
