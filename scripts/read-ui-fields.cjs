const fs=require('node:fs');
for(const file of process.argv.slice(2)){
  const xml=fs.readFileSync(file,'utf8');console.log(file);
  for(const match of xml.matchAll(/<[^>]*resource-id="(?:plan|record)\.[^"]*"[^>]*>/g)){
    const tag=match[0],attrs={};for(const name of ['resource-id','text','hint','showing-hint','enabled','selected'])attrs[name]=tag.match(new RegExp(name+'="([^"]*)"'))?.[1];console.log(JSON.stringify(attrs));
  }
}
