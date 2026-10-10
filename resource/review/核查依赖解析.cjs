// 文档评审用锁文件解析，不创建应用、不安装包、不执行依赖脚本。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const source = JSON.parse(fs.readFileSync(path.join(__dirname, '依赖元数据核查结果.json'), 'utf8'));
if (source.verification.selectedPeers !== 'PASS' || source.verification.nodeEngines !== 'PASS') throw new Error('先修正元数据检查失败');
const dir = path.join(__dirname, 'dependency-resolution');
fs.mkdirSync(dir, { recursive: true });
const manifest = { name: 'plancheckin-dependency-audit', version: '0.0.0', private: true, description: '仅用于技术文档依赖解析，非应用工程', packageManager: source.packageManager, engines: { node: '>=24.3.0 <25', pnpm: '10.28.2' }, dependencies: {}, devDependencies: {} };
for (const item of source.packages.filter(item => item.name !== 'pnpm').sort((a,b) => a.name.localeCompare(b.name))) manifest[item.scope === 'development' ? 'devDependencies' : 'dependencies'][item.name] = item.version;
fs.writeFileSync(path.join(dir, 'package.json'), JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(path.join(dir, 'pnpm-workspace.yaml'), 'nodeLinker: hoisted\nautoInstallPeers: false\nstrictPeerDependencies: true\n');
const pnpmEntry = process.env.REVIEW_PNPM_ENTRY || 'D:/xiang/CX_application/1_Configuration_Files/Front_Rear_END/nodeJS/node_modules/corepack/dist/pnpm.js';
if (!fs.existsSync(pnpmEntry)) throw new Error('通过REVIEW_PNPM_ENTRY指定现有pnpm/Corepack入口');
const common = [pnpmEntry, '--dir', dir, 'install', '--lockfile-only', '--ignore-scripts', '--strict-peer-dependencies', '--config.auto-install-peers=false', '--config.engine-strict=true', '--registry=https://registry.npmjs.org/', '--store-dir', path.join(dir,'store'), '--config.cache-dir=' + path.join(dir,'metadata-cache')];
const runs = [];
// 只重建此评审脚本自己的锁文件，确保首轮实际解析完整图。
const lockFile = path.join(dir, 'pnpm-lock.yaml');
if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile);
for (const frozen of [false, true]) {
  const run = spawnSync(process.execPath, [...common, ...(frozen ? ['--frozen-lockfile'] : [])], { encoding: 'utf8', windowsHide: true, timeout: 180000, maxBuffer: 8 * 1024 * 1024 });
  const output = (run.stdout || '') + (run.stderr || '');
  fs.writeFileSync(path.join(dir, frozen ? 'frozen-resolution.log' : 'resolution.log'), output);
  runs.push({ mode: frozen ? 'frozen_lockfile_only' : 'lockfile_only', exitCode: run.status, status: run.status === 0 && !/Issues with peer|ERR_PNPM|missing peer/.test(output) ? 'PASS' : 'FAIL', error: run.error?.message || null });
  if (runs.at(-1).status !== 'PASS') break;
}
const sha256 = file => fs.existsSync(file) ? crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') : null;
const lock = fs.existsSync(lockFile) ? fs.readFileSync(lockFile, 'utf8') : '';
if (/^\s*(?:metadata-cache:|(?:specifier|version):\s*['"]?(?:link:|file:))/m.test(lock)) throw new Error('锁文件混入本地路径依赖');
const result = { checkedAt: new Date().toISOString(), scope: 'documentation_dependency_resolution_only', analyzerNode: process.version, packageManager: source.packageManager, directPackages: Object.keys(manifest.dependencies).length + Object.keys(manifest.devDependencies).length, metadataSha256: sha256(path.join(__dirname,'依赖元数据核查结果.json')), manifestSha256: sha256(path.join(dir,'package.json')), lockSha256: sha256(lockFile), strictPeers: true, autoInstallPeers: false, ignoreScripts: true, runs, knownTransitiveDeprecations: ['uuid@7.0.3'], verification: { resolution: runs.length === 2 && runs.every(run => run.status === 'PASS') ? 'PASS' : 'FAIL', packageInstall: 'NOT_RUN', metroBundle: 'NOT_RUN', nativeBuild: 'NOT_RUN', emulator: 'NOT_RUN', release: 'NOT_RUN' } };
fs.writeFileSync(path.join(__dirname,'依赖解析核查结果.json'), JSON.stringify(result,null,2) + '\n');
console.log(JSON.stringify(result));
if (result.verification.resolution !== 'PASS') process.exitCode = 1;
