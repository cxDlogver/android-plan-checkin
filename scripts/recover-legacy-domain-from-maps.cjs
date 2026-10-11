const fs=require('node:fs'),path=require('node:path'),{sha}=require('./p1.cjs'),state=require('./progress.cjs').read();
for(const key of ['domain-tests','validation-acceptance-tests']){
 const command=state.commands[key],files=JSON.parse(fs.readFileSync(path.join(path.dirname(command.record),'source-snapshot.json'),'utf8')),expected=files.find(f=>f.path==='src/domain/commands.ts').sha256,matches=[];
 for(const name of fs.readdirSync('.artifacts/apk/release').filter(n=>n.endsWith('.map'))){const file='.artifacts/apk/release/'+name,map=JSON.parse(fs.readFileSync(file,'utf8'));for(let i=0;i<map.sources.length;i++)if(map.sources[i].replaceAll('\\','/').endsWith('src/domain/commands.ts')){const source=map.sourcesContent[i];for(const [ending,text]of [['LF',source],['CRLF',source.replace(/\r?\n/g,'\r\n')]])if(sha(text)===expected)matches.push({file,mapSha256:sha(fs.readFileSync(file)),index:i,source:map.sources[i],ending,sourceSha256:sha(text)});}}
 console.log(JSON.stringify({key,expected,matches}));
}
