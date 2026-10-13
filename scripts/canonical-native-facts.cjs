function stable(value){if(Array.isArray(value))return value.map(stable);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]));return value;}
module.exports=facts=>Object.fromEntries(Object.keys(facts).sort().map(table=>[table,facts[table].map(stable).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)))]));
