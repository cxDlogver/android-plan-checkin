const fs=require('node:fs'),ts=require('typescript'),{createHash}=require('node:crypto');
const findings=[];
function scan(directory){for(const item of fs.readdirSync(directory,{withFileTypes:true})){const file=`${directory}/${item.name}`;if(item.isDirectory())scan(file);else if(file.endsWith('.tsx')){
  const source=fs.readFileSync(file,'utf8'),tree=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),edits=[];
  function visit(node){if(ts.isJsxText(node)&&!node.text.trim()&&node.text.includes(' ')){
    const parent=node.parent,tag=ts.isJsxElement(parent)?parent.openingElement.tagName.getText(tree):'fragment';
    if(!['Text','Body'].includes(tag))edits.push({start:node.pos,end:node.end,tag});
  }ts.forEachChild(node,visit);}visit(tree);
  if(edits.length){let updated=source;for(const edit of edits.sort((a,b)=>b.start-a.start))updated=updated.slice(0,edit.start)+updated.slice(edit.end);fs.writeFileSync(file,updated);findings.push({file,removedWhitespaceNodes:edits.length,beforeSha256:createHash('sha256').update(source).digest('hex'),afterSha256:createHash('sha256').update(updated).digest('hex')});}
}}
}
scan('src');scan('app');
fs.writeFileSync('resource/progress/jsx-space-fix.json',JSON.stringify({recordedAt:new Date().toISOString(),cause:'Actual Android runtime: Text strings must be rendered within a Text component',scope:'Whitespace JSX text children of non-text components only; text component contents preserved',findings},null,2)+'\n');console.log(JSON.stringify(findings));
