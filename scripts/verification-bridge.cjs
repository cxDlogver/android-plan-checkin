const fs=require('node:fs');
const http=require('node:http');
const {randomUUID}=require('node:crypto');
const WebSocketServer=require('ws').Server;
const {DeviceDriver}=require('./device-driver.cjs');
const actions=new Set(['capture','clock','fixture','factsFixture','fault','refresh','faultStatus','readInitialization','settingsVersion','navigate','command','sqlCase','connectionInfo','initializationProbe','migrationProbe','migrationStatus','dateProbe','timezoneProbe','calendarProbe','query','cleanReceipts']);
class VerificationClient {
  constructor(api){this.api=Number(api);this.contextId=null;}
  async status(){const response=await fetch('http://127.0.0.1:8098/status',{signal:AbortSignal.timeout(3000)});if(!response.ok)throw new Error(`Bridge status ${response.status}`);return response.json();}
  async call(action,payload={}){
    if(!actions.has(action))throw new Error('Unsupported verification action');
    let response;
    try{response=await fetch('http://127.0.0.1:8098/request',{method:'POST',headers:{'content-type':'application/json','connection':'close'},body:JSON.stringify({action,payload,api:this.api,contextId:this.contextId}),signal:AbortSignal.timeout(60000)});}
    catch(error){throw new Error(`${error.message}; ${error.cause?.code||''} ${error.cause?.message||''}`);}
    const message=await response.json();if(!response.ok||!message.ok)throw new Error(message.error||`Bridge request ${response.status}`);
    if(this.contextId&&message.result.contextId!==this.contextId)throw new Error('JavaScript context changed during verification');
    this.contextId=message.result.contextId;return message.result;
  }
  async waitReady(timeout=90000){
    const deadline=Date.now()+timeout;
    while(Date.now()<deadline){try{const state=await this.status();if(state.connected&&state.hello?.api===this.api)return state;}catch{}await new Promise(resolve=>setTimeout(resolve,1000));}
    throw new Error('Development verification bridge did not connect');
  }
}
async function serve(api){
  const device=new DeviceDriver(String(api),'.cache/verification-bridge');
  const identity=device.identity();
  device.adb(['reverse','tcp:8097','tcp:8097']);
  const wss=new WebSocketServer({host:'127.0.0.1',port:8097,path:'/plancheckin-verification',maxPayload:8*1024*1024});
  let connected=null,hello=null;
  const pending=new Map();
  const sendJson=(response,status,data)=>{response.writeHead(status,{'content-type':'application/json','cache-control':'no-store'});response.end(JSON.stringify(data));};
  wss.on('connection',socket=>{
    let admitted=false;
    const admissionTimer=setTimeout(()=>{if(!admitted)socket.close(1008,'Identity required');},5000);
    socket.on('message',data=>{
      try{
        const message=JSON.parse(data.toString());
        if(!admitted){
          if(message.type!=='hello'||message.applicationId!==device.package||message.api!==Number(api)||message.protocol!==1||typeof message.contextId!=='string')return socket.close(1008,'Wrong development identity');
          if(connected)connected.close(1000,'Replaced application context');
          admitted=true;clearTimeout(admissionTimer);connected=socket;hello=message;
          fs.writeFileSync(`.cache/verification-bridge/api${api}.json`,JSON.stringify({identity,hello,connectedAt:new Date().toISOString()},null,2)+'\n');
          console.log(`Connected API${api} ${message.applicationId} context ${message.contextId}`);return;
        }
        if(connected!==socket)return;
        const request=pending.get(message.id);if(!request)return;
        pending.delete(message.id);clearTimeout(request.timer);
        const directory='.cache/verification-bridge/responses';fs.mkdirSync(directory,{recursive:true});
        fs.writeFileSync(`${directory}/${message.id}.json`,JSON.stringify({completedAt:new Date().toISOString(),request:request.message,response:message},null,2)+'\n');
        sendJson(request.response,message.ok?200:422,message);
      }catch{socket.close(1008,'Invalid bridge message');}
    });
    socket.on('close',()=>{
      clearTimeout(admissionTimer);
      if(connected===socket){connected=null;for(const [id,request]of pending){clearTimeout(request.timer);sendJson(request.response,503,{ok:false,error:'Application context disconnected'});pending.delete(id);}}
    });
  });
  const server=http.createServer(async(request,response)=>{
    if(request.headers.origin)return sendJson(response,403,{ok:false,error:'Browser requests are not permitted'});
    if(request.method==='GET'&&request.url==='/status')return sendJson(response,200,{connected:!!connected,identity,hello});
    if(request.method!=='POST'||request.url!=='/request')return sendJson(response,404,{ok:false,error:'Unknown bridge endpoint'});
    try{
      let data='';for await(const part of request){data+=part;if(data.length>100000)return sendJson(response,413,{ok:false,error:'Request too large'});}
      const message=JSON.parse(data);
      if(!actions.has(message.action)||message.api!==Number(api))return sendJson(response,400,{ok:false,error:'Unsupported action or wrong API'});
      if(!connected)return sendJson(response,503,{ok:false,error:'Development application is disconnected'});
      if(message.contextId&&message.contextId!==hello.contextId)return sendJson(response,409,{ok:false,error:'JavaScript context changed during verification'});
      const id=randomUUID();
      const timer=setTimeout(()=>{pending.delete(id);sendJson(response,504,{ok:false,error:'Verification response timed out'});},55000);
      pending.set(id,{response,timer,message});connected.send(JSON.stringify({id,action:message.action,payload:message.payload}));
    }catch(error){sendJson(response,400,{ok:false,error:error.message});}
  });
  server.listen(8098,'127.0.0.1',()=>console.log(`API${api} verification bridge: WS 127.0.0.1:8097, HTTP 127.0.0.1:8098`));
  const close=()=>{for(const request of pending.values()){clearTimeout(request.timer);sendJson(request.response,503,{ok:false,error:'Bridge stopped'});}pending.clear();wss.close();server.close();if(connected)connected.close();};
  process.once('SIGINT',close);process.once('SIGTERM',close);
}
async function waitForMetro(timeout=180000){
  const deadline=Date.now()+timeout;
  while(Date.now()<deadline){try{const response=await fetch('http://127.0.0.1:8081/status',{signal:AbortSignal.timeout(4000)});if(response.ok&&(await response.text()).trim()==='packager-status:running')return;}catch{}await new Promise(resolve=>setTimeout(resolve,1000));}
  throw new Error('Task Metro did not become healthy before development launch');
}
module.exports={VerificationClient,waitForMetro};
if(require.main===module){if(!['29','36'].includes(process.argv[2]))throw new Error('Specify the project API29 or API36 device');serve(process.argv[2]).catch(error=>{console.error(error.message);process.exitCode=1;});}
