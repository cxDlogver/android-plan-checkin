const fs=require('node:fs');
const dump=fs.readFileSync('.cache/gradle-thread-dump.txt','utf8').replace(/^\uFEFF/,'');
const threads=dump.split(/(?=^"[^"\r\n]+" #)/m);
const candidates=threads.filter(thread=>/java\.net\.|org\.apache\.http|jdk\.internal\.net|ExecHandle|ProcessImpl|ExternalProcess|"included builds"|"Execution worker"/.test(thread));
for(const thread of threads.filter(thread=>thread.startsWith('"')))console.log(thread.split(/\r?\n/).slice(0,4).join('\n'));
for(const thread of candidates.filter(thread=>!thread.startsWith('"File lock request listener')).slice(0,8))console.log(thread.split(/\r?\n/).slice(0,26).join('\n'));
