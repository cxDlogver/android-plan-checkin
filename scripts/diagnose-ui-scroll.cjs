const {open}=require('./bdd-ui-session.cjs');
const fs=require('node:fs');
async function main(){const {device,client}=await open(process.argv[2]||'36','.cache/scroll-diagnostic');try{
  await client.call('navigate',{route:'/plans/new'});await device.waitSource(s=>s.includes('plan.name'));
  await device.save('initial');console.log('Down',await device.scroll('down'));const bottom=await device.save('bottom');console.log('scrollables',bottom.match(/<[^>]*scrollable="true"[^>]*>/g));
  console.log('Up',await device.scroll('up'));const after=await device.save('after-up');console.log('name after up',after.includes('resource-id="plan.name"'));
  const scrollId=await device.element('xpath','//*[@scrollable="true" and not(self::android.widget.EditText)]');
  console.log('Targeted up',await device.request(device.endpoint('execute/sync'),'POST',{script:'mobile: scrollGesture',args:[{elementId:scrollId,direction:'up',percent:.8}]}));
  console.log('targeted name',(await device.save('targeted-up')).includes('resource-id="plan.name"'));
}finally{await device.close();}}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
