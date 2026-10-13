const fs=require('node:fs'),{sha}=require('./p1.cjs'),{read}=require('./acceptance-evidence.cjs');
module.exports=item=>{
 if(!/^AC(?:016|023|024|025|029|036|045|046|049|066|105|107|120)-/.test(item.key))throw new Error('Unapproved original Provider success branch');
 const file='src/state/AppProvider.tsx',current=fs.readFileSync(file,'utf8'),original=read(item,'inputs.json').source.find(s=>s.path===file);
 if(sha(current)===original?.sha256)return {file,originalSha256:original.sha256,currentSha256:sha(current),scope:'Whole Provider identical.'};
 const withoutCallback=current.replace('now, attachReadInitialization','now').replace('  useEffect(()=>{if(service)attachReadInitialization(async()=>{setSnapshot(null);await refresh();});},[service,refresh]);\n','');
 let body=withoutCallback,scope='Only the later development read-initialization callback differs. The original actual successful-read rows never invoke that callback; every other Provider byte is identical.';
 if(sha(body)!==original?.sha256){body=body.replace('ActivityIndicator, Modal, View','ActivityIndicator, View').replace("if(error)return {ok:false,code:'STORAGE_IO'};",'');const begin=body.indexOf('  return <Context.Provider value={value}>{children}<Modal'),end=body.indexOf('\n}',begin);if(begin<0||end<0)throw new Error('Known read-error overlay absent');body=body.slice(0,begin)+'  return <Context.Provider value={value}>{children}</Context.Provider>;'+body.slice(end);scope='Only the later development read-initialization callback, read-error overlay and error guard differ. All retained original rows have successful reads and invoke neither read-fault initialization nor retry; error remains null, the overlay is hidden and the guard false. Exact complete original bootstrap, refresh, date listener, envelope and successful execute body is reconstructed. Native/UI read-error behavior is accepted separately by AC082/106/012.';}
 if(sha(body)!==original?.sha256)throw new Error('Unexpected original Provider difference');
 return {file,originalSha256:original.sha256,currentSha256:sha(current),reconstructedCompleteOriginalSha256:sha(body),scope};
};
