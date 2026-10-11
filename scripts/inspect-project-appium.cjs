(async()=>{const r=await fetch('http://127.0.0.1:4723/sessions').then(r=>r.json());console.log(JSON.stringify(r));})().catch(e=>{console.error(e.message);process.exitCode=1;});
