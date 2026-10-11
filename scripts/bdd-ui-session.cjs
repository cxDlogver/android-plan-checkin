const fs=require('node:fs'),{randomUUID}=require('node:crypto'),{createRun}=require('./evidence-run.cjs'),{snapshot,sha}=require('./p1.cjs'),{DeviceDriver,decode}=require('./device-driver.cjs'),{VerificationClient,waitForMetro}=require('./verification-bridge.cjs');
const node=function(){return require('./task-env.cjs').node;};
const sourceFiles=['app','src/features','src/ui','src/state','src/domain','src/application','src/infrastructure/database','src/verification'];
function tag(xml,id){return xml.match(new RegExp('<[^>]*resource-id="'+id.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'"[^>]*>'))?.[0];}
function attr(xml,id,name){const value=tag(xml,id)?.match(new RegExp(name+'="([^"]*)"'))?.[1];return value===undefined?undefined:decode(value);}
async function navigate(client,device,route,params,mode='replace'){
  const foreground=await device.source();
  if(!foreground.includes(`package="${device.package}"`))device.adb(['shell','am','start','-W','-n',`${device.package}/.MainActivity`]);
  await client.call('navigate',{route,params,mode});
  const source=await device.waitSource(s=>s.includes('放弃未保存内容？')||(route==='/native'?s.includes('原生模块验证'):!s.includes('原生模块验证')),15000);
  if(source.includes('放弃未保存内容？'))await device.text('确认');
  if(route==='/native')await device.waitSource(s=>s.includes('原生模块验证'));
}
class UiCase {
  constructor(run,device,client){this.run=run;this.device=device;this.client=client;this.step=0;this.now=Date.parse('2026-10-09T04:00:00Z');}
  check(id,expected,actual){this.run.check(id,expected,actual);}
  async frame(name){const source=await this.device.save(`${++this.step}-${name}`);this.run.write(`step-${this.step}.json`,{name,at:new Date().toISOString()});return source;}
  async click(id){await this.device.clickVisible(id);await new Promise(resolve=>setTimeout(resolve,350));}
  async input(id,text){await this.device.seek(id);await this.device.input(id,text);try{await this.device.hideKeyboard();}catch{}await new Promise(resolve=>setTimeout(resolve,350));}
  async nav(route,params){const target=route.replace('[planId]',params?.planId||'').replace('[recordId]',params?.recordId||'');await navigate(this.client,this.device,'/native');if(target.startsWith('/records/')||target==='/plans/new'){await navigate(this.client,this.device,'/(tabs)/today');await navigate(this.client,this.device,target,params,'push');}else if(/\/plans\/[^/]+\/edit$/.test(target)){await navigate(this.client,this.device,target.replace(/\/edit$/,''),params);await navigate(this.client,this.device,target,params,'push');}else await navigate(this.client,this.device,target,params);}
  async clock(instant){this.now=Date.parse(instant);this.run.write(`step-${++this.step}-clock.json`,await this.client.call('clock',{instant}));await new Promise(resolve=>setTimeout(resolve,400));}
  async capture(name){const data=await this.client.call('capture');this.run.write(`${name}.json`,data);return data.snapshot;}
  async type(type){await this.click(`plan.type.${type}`);await this.device.waitSource(source=>source.includes('切换计划类型'));await this.device.text('确认');await this.device.waitSource(source=>attr(source,`plan.type.${type}`,'selected')==='true'&&!source.includes('切换计划类型'));}
  async create(type='fixed',on='2026-10-01',options={}){
    await this.clock(`${on}T12:00:00+08:00`);const planId=randomUUID(),envelope={commandId:randomUUID(),issuedAtMs:this.now,kind:'CreatePlan',payload:{planId,name:'BDD 页面夹具',description:'',type,direction:'do',...(type==='one_time'?{dueOn:'2026-10-10'}:{startsOn:on,endOn:null,...(type==='fixed'?{weekdayMask:127}:{weeklyTarget:3})}),...options}};
    const result=await this.client.call('command',{envelope});this.run.write(`step-${++this.step}-given-create.json`,{envelope,result});this.check('Given.plan-created','OK',result.result.code);return planId;
  }
  async command(kind,payload,expected='OK'){
    const envelope={commandId:randomUUID(),issuedAtMs:this.now,kind,payload},result=await this.client.call('command',{envelope});this.run.write(`step-${++this.step}-given-command.json`,{envelope,result});this.check(`step-${this.step}.command-result`,expected,result.result.code);return result.result;
  }
  async ref(planId){const s=await this.client.call('capture');return {planId,expectedPlanRevision:s.snapshot.facts.plans.find(p=>p.id===planId).revision};}
  async record(planId,on,result='success',note=''){
    await this.clock(`${on}T12:00:00+08:00`);const recordId=randomUUID();await this.command('SubmitCycleRecord',{...await this.ref(planId),recordId,businessOn:on,result,note,confirmedToday:on,confirmedEntryKind:'ordinary'});return recordId;
  }
  async newPlan(type,name='BDD 新计划'){
    await this.nav('/(tabs)/today');await this.click('plan.create');await this.device.waitSource(s=>s.includes('plan.name'));if(type!=='fixed')await this.type(type);await this.input('plan.name',name);if(type==='fixed')await this.click('plan.weekday.everyday');
  }
  async textPresent(id,text){let visible=false;try{visible=(await this.device.seeText(text)).includes(text);}catch{}this.check(id,true,visible);}
  async property(id,name){await this.device.seek(id);const xml=await this.device.source();return name==='text'&&attr(xml,id,'showing-hint')==='true'?'':attr(xml,id,name);}
  async savePlan(){await this.click('plan.save');await this.device.waitSource(s=>s.includes('计划详情')||s.includes('请检查输入')||s.includes('日期不能')||s.includes('日期不存在'));
  }
  async unchanged(before,id){const after=await this.capture('after-facts');this.check(id,before.facts,after.facts);}
  async restart(){await this.device.close();this.client.contextId=null;await this.device.open();this.device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');await this.device.waitSource(s=>s.includes('今日')||s.includes('原生模块验证'),120000);this.device.deepLink('plancheckin-dev://native');await this.client.waitReady();await this.clock(new Date(this.now).toISOString());}
}
async function open(api,directory){const device=new DeviceDriver(api,directory),client=new VerificationClient(api);device.identity();await waitForMetro();device.adb(['reverse','tcp:8081','tcp:8081']);await device.open();device.deepLink('plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');await device.waitSource(s=>s.includes('今日')||s.includes('原生模块验证'),120000);device.deepLink('plancheckin-dev://native');await client.waitReady();return {device,client};}
async function runCases(api,definitions,select=[],config){
  const {device,client}=await open(api,'.cache/bdd-ui');
  const identity=device.identity(),width=identity.density.includes('480')?360:393,font=Number(identity.fontScale),configId=config||`api${api}-${width}dp-font${font}`;
  try{
    for(const [ac,rows]of Object.entries(definitions)){if(select.length&&!select.includes(ac)&&!select.some(s=>s.startsWith(ac+'/')))continue;
      for(const [row,fn]of Object.entries(rows)){if(select.length&&!select.includes(ac)&&!select.includes(ac+'/'+row))continue;
        await device.request(device.endpoint('timeouts'));await client.waitReady(5000);
        const build=require('./progress.cjs').read().commands['native-debug'];
        const run=createRun(`${ac}-${row}-${configId}`,{api,configId,apk:build.artifacts.filter(f=>f.path.endsWith('.apk')),lockfileSha256:sha(fs.readFileSync('pnpm-lock.yaml')),source:snapshot(sourceFiles),verificationHarness:{caseFunction:fn.toString(),shared:snapshot(['scripts/bdd-ui-session.cjs','scripts/device-driver.cjs'])}},['IP26'],{caseId:ac,rowId:row,configId,...(fn.verificationPhase?{phase:fn.verificationPhase}:{})});if(!run)continue;
        device.directory=run.directory;const t=new UiCase(run,device,client);let error=null;
        const logPath=require('node:path').join(require('./task-env.cjs').toolRoot,'logs/appium-4723.log'),logStart=fs.existsSync(logPath)?fs.statSync(logPath).size:0;
        try{run.write('device.json',device.identity());await client.call('fault',{point:null});await t.clock('2026-10-09T12:00:00+08:00');run.write('fixture.json',await client.call('fixture',{name:'F01',zone:'Asia/Shanghai',confirm:'RESET_ISOLATED_DEV_DATABASE'}));await fn(t);await t.capture('final-native-facts');await t.frame('final');}
        catch(e){error=e;console.error(`${ac}/${row}: ${e.message}`);try{await t.frame('failure');await t.capture('failure-native-facts');}catch{}}
        if(fs.existsSync(logPath)){const size=fs.statSync(logPath).size-logStart;if(size>=0){const descriptor=fs.openSync(logPath,'r'),log=Buffer.alloc(size);fs.readSync(descriptor,log,0,size,logStart);fs.closeSync(descriptor);run.write('appium.log',log.toString('utf8'));}}
        run.finish(error,['UI When steps use actual Appium/native product controls. Bridge commands and fixture restoration are recorded only for Given preparation, scoped service rejection companions, clocks, faults and readback.']);
        device.directory='.cache/bdd-ui/navigation';fs.mkdirSync(device.directory,{recursive:true});
        try{await navigate(client,device,'/native');}catch{}
      }
    }
  }finally{try{await client.call('fault',{point:null});await client.call('clock',{instant:null});}catch{}await device.close();}
}
module.exports={runCases,UiCase,open,attr,tag};
