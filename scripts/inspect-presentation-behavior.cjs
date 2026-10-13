const fs=require('node:fs'),ts=require('typescript');
const root='resource/progress/visual-alignment',baseline=JSON.parse(fs.readFileSync(root+'/baseline.json'));
function hasJsx(n){if(ts.isJsxElement(n)||ts.isJsxSelfClosingElement(n)||ts.isJsxFragment(n))return true;let found=false;ts.forEachChild(n,c=>{if(hasJsx(c))found=true;});return found;}
function functions(body){const ast=ts.createSourceFile('f.tsx',body,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),out=[];function scan(n){if((ts.isArrowFunction(n)||ts.isFunctionDeclaration(n))&&!hasJsx(n))out.push(n.getText(ast));ts.forEachChild(n,scan);}scan(ast);return out.sort();}
const differences=[];
for(const p of baseline.files.filter(p=>p.path.startsWith('src/features/'))){const old=functions(fs.readFileSync(root+'/'+p.path.replaceAll('/','__')+'.before','utf8')),current=functions(fs.readFileSync(p.path,'utf8'));differences.push({file:p.path,removed:old.filter(v=>!current.includes(v)),added:current.filter(v=>!old.includes(v))});}
fs.writeFileSync(root+'/handler-differences.json',JSON.stringify(differences,null,2)+'\n');console.log(JSON.stringify(differences,null,2));
