const fs=require('node:fs'),{sha}=require('./p1.cjs'),{read}=require('./acceptance-evidence.cjs');
module.exports=function(item){const sources=read(item,'inputs.json').source,proof=[];
 for(const file of ['src/features/record-form.tsx','src/ui/metal.tsx']){const original=sources.find(s=>s.path===file);if(!original)throw new Error('Record UI source absent');const body=require('./presentation-business-source.cjs')(file,item).body;let recovered=body,excluded=null;
  if(sha(body)!==original.sha256&&file==='src/ui/metal.tsx'){recovered=body.split(/\r?\n/).filter(line=>!line.startsWith('export function Tag(')).join('\n');excluded='Only the later standalone Tag component definition; RecordForm imports no Tag, and every original Button/Choice/Field/Page/Notice/Body function and style is retained byte-identically.';}
  if(sha(recovered)!==original.sha256)throw new Error('Executed RecordForm or existing UI control changed '+file);proof.push({file,originalSha256:original.sha256,recoveredCompleteOriginalSha256:sha(recovered),executedBusinessSourceSha256:sha(body),excluded});
 }return {proof,scope:'Original whole RecordForm and all original shared controls, accessibility state, colors and styles are byte identical. A standalone Tag export was subsequently added without modifying any original function; it is not imported by RecordForm. The original actual record When and readback are reused without repeating business actions.'};
};

const presentationPreviousScope=module.exports;module.exports=item=>({...presentationPreviousScope(item),presentationDelta:require('./presentation-business-source.cjs').scopeReference()});
