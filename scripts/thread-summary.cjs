const fs=require('node:fs');
const blocks=fs.readFileSync('.cache/native-thread-dump.log','utf8').split(/\r?\n\r?\n/);
for(const block of blocks)if(/^"/.test(block)&&/http|ssl|socket|Download|Execution worker|included builds/i.test(block)&&!/^"(Daemon|Handler|Incoming)/.test(block))console.log(block.split(/\r?\n/).slice(0,45).join('\n'));
