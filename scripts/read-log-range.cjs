const fs=require('node:fs');
module.exports=function(file,start){const length=Math.max(0,fs.statSync(file).size-start),bytes=Buffer.alloc(length),fd=fs.openSync(file,'r');try{let read=0;while(read<length){const n=fs.readSync(fd,bytes,read,length-read,start+read);if(!n)break;read+=n;}return bytes.subarray(0,read);}finally{fs.closeSync(fd);}};
