const fs=require('node:fs');
const keys=['PLANCHECKIN_KEYSTORE','PLANCHECKIN_STORE_PASSWORD','PLANCHECKIN_KEY_ALIAS','PLANCHECKIN_KEY_PASSWORD'];
console.log(JSON.stringify({configured:keys.every(key=>!!process.env[key]),keyFilePresent:!!process.env.PLANCHECKIN_KEYSTORE&&fs.existsSync(process.env.PLANCHECKIN_KEYSTORE),missing:keys.filter(key=>!process.env[key])}));
