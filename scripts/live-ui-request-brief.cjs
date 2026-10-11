const fs=require('node:fs'),path=require('node:path'),{toolRoot}=require('./task-env.cjs');
const file=path.join(toolRoot,'logs/appium-4723.log'),size=fs.statSync(file).size,length=Math.min(size,128000),buffer=Buffer.alloc(length),fd=fs.openSync(file,'r');fs.readSync(fd,buffer,0,length,size-length);fs.closeSync(fd);
for(const line of buffer.toString('utf8').split(/\r?\n/).filter(l=>l.includes('[HTTP] -->')).slice(-12))console.log(line.slice(0,900));
