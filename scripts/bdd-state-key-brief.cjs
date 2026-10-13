const state=require('./progress.cjs').read(),pattern=new RegExp(process.argv[2]||'^AC094');
for(const [key,c]of Object.entries(state.commands))if(pattern.test(key))console.log(JSON.stringify({key,status:c.status,record:c.record}));
