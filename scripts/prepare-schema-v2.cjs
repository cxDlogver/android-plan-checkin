const fs=require('node:fs');
const guards={
 plans:['id','type','direction','created_at_ms','created_on','starts_on'],
 cycle_records:['id','plan_id','business_on','entry_kind','submitted_at_ms'],
 one_time_results:['id','plan_id','business_on','entry_kind','submitted_at_ms','due_rule_version_id'],
 cycle_record_originals:['record_id','original_result','original_note'],
 one_time_result_originals:['result_id','original_outcome','original_note'],
 rule_versions:['id','plan_id','kind','effective_on','revision','value_json','created_at_ms'],
 lifecycle_events:['id','plan_id','kind','source_key','effective_on','effective_at_ms','reason','requested_at_ms'],
};
const sql='-- Schema 2 strengthens existing immutable facts without changing table layouts or stored rows.\n'+Object.entries(guards).map(([table,columns])=>`CREATE TRIGGER immutable_${table}\nBEFORE UPDATE ON ${table}\nWHEN ${columns.map(column=>`OLD.${column} IS NOT NEW.${column}`).join(' OR ')}\nBEGIN\n  SELECT RAISE(ABORT, 'immutable ${table}');\nEND;\n`).join('\n');
fs.writeFileSync('resource/technical/schema-v2.sql',sql);
fs.writeFileSync('src/infrastructure/database/schema-v2.ts',`// DDL source: resource/technical/schema-v2.sql\nexport const schemaV2=${JSON.stringify(sql)};\nexport const immutableTables=${JSON.stringify(Object.keys(guards))} as const;\n`);
let migrations=fs.readFileSync('src/infrastructure/database/migrations.ts','utf8');
if(!migrations.includes('currentSchemaVersion=1'))throw new Error('Expected shipped V1 baseline absent');
migrations=migrations.replace("import { schemaV1 } from './schema';","import { schemaV1 } from './schema';\nimport { schemaV2 } from './schema-v2';").replace('currentSchemaVersion=1','currentSchemaVersion=2').replace('[{version:1,sql:schemaV1}]','[{version:1,sql:schemaV1},{version:2,sql:schemaV2}]');
fs.writeFileSync('src/infrastructure/database/migrations.ts',migrations);
const file='src/features/shared.tsx';let shared=fs.readFileSync(file,'utf8').replace('Body, Button, Metal, colors','Body, Button, Metal, Tag, colors');
shared=shared.replace('<Body style={{fontSize:12,color:colors.muted}}>{typeLabel[plan.type]}', '<Tag testID={`plan.tag.${plan.id}`}>{typeLabel[plan.type]}').replace("{statusLabel[status(snapshot.facts,plan.id,snapshot.asOfMs)]}</Body>","{statusLabel[status(snapshot.facts,plan.id,snapshot.asOfMs)]}</Tag>");
fs.writeFileSync(file,shared);
const config='app.config.ts';fs.writeFileSync(config,fs.readFileSync(config,'utf8').replace("PLANCHECKIN_VERSION_CODE || '1'","PLANCHECKIN_VERSION_CODE || '2'"));
fs.appendFileSync('resource/progress/技术执行调整.md','\n## Schema 2：冻结历史事实的 SQLite 防护及初版覆盖升级演练\n\n2026-10-11：保留 schema 1 的九张表、索引和全部字段布局，新增七个 UPDATE 触发器。计划身份/类型/方向/起始日期、记录首次提交字段和 due 引用、历史原值、规则及状态事件原始字段发生实际变化时拒绝写入；合法名称、说明、结果更正、备注、修订和申请取消继续允许。删除与原有级联规则不变。迁移复用原全链事务，最后提交 user_version=2。\n\n旧版为已保存的 schema 1、versionCode=1、正式同包同签名“旧 schema 验证包”，不能声称已有正式发布旧版。新版默认 versionCode=2；覆盖升级须保留固定时区、历史原值、待生效规则/状态及统计事实，并在 API29/36 分别留证。该调整本身不代表验收已通过；新增迁移/触发器范围单独验证，原业务断言按未变更函数和证据复用。\n');
console.log('Prepared actual schema 1 → 2 migration, seven immutable-fact guards and visible 1 dp tags.');
