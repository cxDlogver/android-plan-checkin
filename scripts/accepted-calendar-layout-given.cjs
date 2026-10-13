const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{sha}=require('./p1.cjs'),{read}=require('./acceptance-evidence.cjs');
module.exports=function(item){
 const name='six-row-large-fraction-Given.json',direct=item.r.evidence.find(e=>path.basename(e.path)===name);
 if(direct)return {facts:read(item,name),source:{record:item.record,sha256:item.sha256,file:direct}};
 const proof=read(item,'reused-seven-column-native-proof.json');
 assert.equal(sha(fs.readFileSync(proof.record)),proof.sha256,'Closed fixture provenance changed');
 const previous=JSON.parse(fs.readFileSync(proof.record,'utf8')),file=previous.evidence.find(e=>path.basename(e.path)===name);
 assert.ok(file&&proof.evidence.some(e=>e.path===file.path&&e.sha256===file.sha256),'Fixture is outside the accepted reuse scope');
 assert.equal(sha(fs.readFileSync(file.path)),file.sha256);
 return {facts:JSON.parse(fs.readFileSync(file.path,'utf8')),source:{accepted:item.record,acceptedSha256:item.sha256,record:proof.record,sha256:proof.sha256,file,scope:'Only the immutable original Given fixture is reused; the failed report is not claimed as successful current layout.'}};
};
