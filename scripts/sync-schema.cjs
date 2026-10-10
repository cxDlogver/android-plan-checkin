const fs=require('node:fs');
const sql=fs.readFileSync('resource/technical/schema-v1.sql','utf8').replace(/PRAGMA user_version = 1;\s*$/,'');
fs.mkdirSync('src/infrastructure/database',{recursive:true});
fs.writeFileSync('src/infrastructure/database/schema.ts',`// 原始DDL：resource/technical/schema-v1.sql；user_version由全链迁移事务最后设置。\nexport const schemaV1 = ${JSON.stringify(sql)};\n`);
console.log('已将已确认9表DDL写入应用迁移源码，未重新运行宿主SQL原型验证。');
