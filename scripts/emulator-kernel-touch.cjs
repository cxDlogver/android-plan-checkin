const net=require('node:net'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const clients=new Map();
async function client(d){
 if(clients.has(d.serial))return clients.get(d.serial);
 const port=Number(d.serial.replace('emulator-',''));if(![5560,5562].includes(port))throw new Error('Only disposable project emulators are authorized');
 let pending,buffer='';const socket=net.createConnection({host:'127.0.0.1',port});
 const response=()=>new Promise((resolve,reject)=>{pending={resolve,reject};});
 const banner=response();socket.on('data',chunk=>{buffer+=chunk;const end=buffer.match(/(?:^|\r?\n)(OK|KO:[^\r\n]*)\r?\n/);if(end&&pending){const current=pending;pending=null;const text=buffer;buffer='';if(end[1].startsWith('KO:'))current.reject(new Error('Emulator console rejected kernel event'));else current.resolve(text);}});socket.on('error',error=>{pending?.reject(error);pending=null;});
 await banner;
 const command=async text=>{const result=response();socket.write(text+'\n');return result;};
 // Local emulator console authentication only; the credential is never written to evidence or logs.
 const token=fs.readFileSync(path.join(os.homedir(),'.emulator_console_auth_token'),'utf8').trim();await command('auth '+token);
 const value={command,close:()=>socket.end()};clients.set(d.serial,value);return value;
}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function tap(d,x,y,hold=60){const c=await client(d);await c.command(`event mouse ${x} ${y} 0 1`);await sleep(hold);await c.command(`event mouse ${x} ${y} 0 0`);}
async function swipe(d,x1,y1,x2,y2){const c=await client(d);await c.command(`event mouse ${x1} ${y1} 0 1`);for(let i=1;i<=8;i++){await sleep(20);await c.command(`event mouse ${Math.round(x1+(x2-x1)*i/8)} ${Math.round(y1+(y2-y1)*i/8)} 0 1`);}await c.command(`event mouse ${x2} ${y2} 0 0`);}
function closeAll(){for(const c of clients.values())c.close();clients.clear();}
module.exports={tap,swipe,closeAll};
