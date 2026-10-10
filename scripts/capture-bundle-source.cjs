const fs=require('node:fs'),path=require('node:path'),{snapshot,sha}=require('./p1.cjs'),state=require('./progress.cjs').read();
const build=state.commands['native-release'];
if(process.argv[2]==='--from-start'){
  if(!build?.record&&!build?.logPath)throw new Error('A release build input snapshot is required.');
  const directory=path.dirname(build.record||build.logPath),source=JSON.parse(fs.readFileSync(`${directory}/source-snapshot.json`,'utf8'));
  const files=source.sources.filter(file=>/^(app\/|src\/|plugins\/|assets\/|app.config.ts$|package.json$|pnpm-lock.yaml$|metro.config.cjs$|babel.config.cjs$)/.test(file.path));
  const report={recordedAt:source.startedAt,derivedAt:new Date().toISOString(),scope:'immutable source snapshot captured before Gradle process spawn; verified against actual bundle source map',sourceSnapshot:`${directory}/source-snapshot.json`,sourceSha256:sha(JSON.stringify(files)),files};
  const target=`${directory}/bundle-source-snapshot.json`;if(fs.existsSync(target))throw new Error('Frozen source already exists; do not overwrite evidence.');
  fs.writeFileSync(target,JSON.stringify(report,null,2)+'\n');console.log('Preserved immutable release input source.');process.exit(0);
}
if(build?.status!=='RUNNING')throw new Error('A running release build is required.');
const log=fs.readFileSync(build.logPath,'utf8');if(log.includes('> Task :app:createBundleReleaseJsAndAssets'))throw new Error('The bundle task has started; do not change the source snapshot for this build.');
const files=snapshot(['app','src','plugins','assets','app.config.ts','package.json','pnpm-lock.yaml','metro.config.cjs','babel.config.cjs']);
const report={recordedAt:new Date().toISOString(),scope:'source frozen before release JS bundle task',buildLogBytes:Buffer.byteLength(log),buildLogPrefixSha256:sha(log),sourceSha256:sha(JSON.stringify(files)),files,changesSinceBuildStart:['显示星期使用明确中文文本，避免Android Intl星期语言回退','开发验收报告改为可访问父视图；正式包排除此开发实现']};
fs.writeFileSync(`${path.dirname(build.logPath)}/bundle-source-snapshot.json`,JSON.stringify(report,null,2)+'\n');console.log('Captured release source before bundling.');
