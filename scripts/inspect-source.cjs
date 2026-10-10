const fs=require('node:fs'),path=require('node:path');
function walk(folder){return fs.readdirSync(folder,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(folder,e.name)):path.join(folder,e.name));}
const files=walk('app').concat(walk('src'));
const placeholders=files.flatMap(file=>fs.readFileSync(file,'utf8').split(/\r?\n/).flatMap((line,index)=>/TODO|FIXME|throw new Error\(['"]Not implemented|尚未实现/.test(line)?[{file,line:index+1,text:line.slice(0,150)}]:[]));
console.log(JSON.stringify({sourceFiles:files.length,placeholders,fontFiles:fs.readdirSync('assets/fonts')},null,2));
