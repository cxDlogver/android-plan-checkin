const progress=require('./progress.cjs');
progress.update(state=>{
  const build=state.commands['native-debug'];
  if(build?.status==='PASS'){
    const task=state.tasks.find(task=>task.id==='IP03');
    task.status='IN_PROGRESS';task.blockedReason=null;
    for(const id of ['W1','W4'])if(!task.workDone.includes(id))task.workDone.push(id);
  }
  for(const id of ['IP04','IP05'])state.tasks.find(task=>task.id===id).blockedReason=null;
  state.next='开发APK和API36原生参数/核心产品流程已PASS；复用已有证据。继续API29首次原生检查、长期签名release构建和实际APK审计，再执行尚未完成的离线/视觉/八组合/性能/升级专项。';
});
console.log('Updated native progress; no completed verification repeated.');
