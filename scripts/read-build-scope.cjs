const fs=require('node:fs');
for(const [file,heading,next] of [['resource/acceptance/scenarios/01-工程准入.md','### AC003｜','### AC004｜'],['resource/实施计划-checklist-计划打卡-Android-v1.md','### IP03','### IP04']]){const text=fs.readFileSync(file,'utf8'),start=text.indexOf(heading),end=text.indexOf(next,start+heading.length);console.log(text.slice(start,end<0?start+4500:end));}
