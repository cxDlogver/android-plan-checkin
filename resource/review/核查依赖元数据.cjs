// 只读取官方发布元数据和少量发布包文件，不安装依赖、不运行包内脚本。
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const zlib = require('zlib');
const semver = require(process.env.REVIEW_SEMVER_MODULE || 'C:/Users/xiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/semver');
const registry = 'https://registry.npmjs.org/';
const cache = new Map();
async function request(url, json = true, accept = 'application/vnd.npm.install-v1+json') {
  const response = await fetch(url, { signal: AbortSignal.timeout(45000), headers: json ? { accept } : {} });
  if (!response.ok) throw new Error(`${response.status}: ${url}`);
  return json ? response.json() : Buffer.from(await response.arrayBuffer());
}
function packument(name) {
  if (!cache.has(name)) cache.set(name, request(registry + encodeURIComponent(name)));
  return cache.get(name);
}
async function resolve(name, range) {
  const pack = await packument(name);
  const version = semver.maxSatisfying(Object.keys(pack.versions).filter(version => !semver.prerelease(version)), range);
  if (!version) throw new Error(`No stable ${name} matching ${range}`);
  return request(registry + encodeURIComponent(name) + '/' + version, true, 'application/json');
}
function tarFiles(gzip) {
  const tar = zlib.gunzipSync(gzip, { maxOutputLength: 160 * 1024 * 1024 });
  const result = new Map();
  for (let offset = 0; offset + 512 <= tar.length;) {
    const header = tar.subarray(offset, offset + 512);
    const name = header.subarray(0, 100).toString().split('\0')[0];
    if (!name) break;
    const prefix = header.subarray(345, 500).toString().split('\0')[0];
    const size = parseInt(header.subarray(124, 136).toString().replace(/\0/g, '').trim() || '0', 8);
    if (!Number.isFinite(size) || offset + 512 + size > tar.length) throw new Error('Invalid tar bounds');
    const kind = header[156];
    if (kind === 0 || kind === 48) result.set(prefix ? `${prefix}/${name}` : name, tar.subarray(offset + 512, offset + 512 + size));
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  return result;
}
async function archive(meta) {
  const bytes = await request(meta.dist.tarball, false);
  const [algorithm, expected] = meta.dist.integrity.split(' ' )[0].split('-');
  if (crypto.createHash(algorithm).update(bytes).digest('base64') !== expected) throw new Error(`Integrity mismatch: ${meta.name}`);
  return tarFiles(bytes);
}
async function main() {
  const expo = await resolve('expo', '57.0.x');
  const files = await archive(expo);
  const bundled = JSON.parse(files.get('package/bundledNativeModules.json').toString());
  const runtime = ['react', 'react-native', 'expo-router', 'react-native-safe-area-context', 'react-native-screens', 'expo-linking', 'expo-constants', 'expo-status-bar', 'expo-sqlite', 'expo-localization', 'expo-linear-gradient', 'expo-build-properties', 'expo-font', 'expo-splash-screen', 'react-native-svg', 'expo-crypto', 'expo-application', 'react-dom', 'react-native-gesture-handler', 'react-native-reanimated', 'react-native-worklets'];
  const development = ['expo-dev-client', 'typescript', '@types/react', '@types/luxon', '@types/node', 'babel-preset-expo', 'react-refresh', '@babel/core', '@react-native/metro-config', 'pnpm'];
  const ranges = { expo: expo.version, luxon: '^3', zod: '^4', typescript: '~5.9.2', '@types/react': '~19.2.2', '@types/luxon': '^3', '@types/node': '^24', pnpm: '10.28.2', 'babel-preset-expo': expo.dependencies['babel-preset-expo'], 'react-refresh': expo.dependencies['react-refresh'], '@babel/core': '^7.28.0' };
  for (const name of runtime.concat('expo-dev-client')) {
    if (!bundled[name]) throw new Error(`Missing SDK57 range: ${name}`);
    ranges[name] = bundled[name];
  }
  ranges['@react-native/metro-config'] = bundled['react-native'];
  const selected = new Map([['expo', { meta: expo, scope: 'runtime', range: expo.version }]]);
  const names = runtime.concat(['luxon', 'zod'], development);
  for (let offset = 0; offset < names.length; offset += 4) {
    await Promise.all(names.slice(offset, offset + 4).map(async name => selected.set(name, { meta: await resolve(name, ranges[name]), scope: development.includes(name) ? 'development' : 'runtime', range: ranges[name] })));
  }
  const provided = new Map([...selected].map(([name, value]) => [name, value.meta.version]));
  const checks = [], missing = [];
  for (const [name, { meta }] of selected) {
    for (const [peer, range] of Object.entries(meta.peerDependencies || {})) {
      const optional = !!meta.peerDependenciesMeta?.[peer]?.optional;
      let version = provided.get(peer), provider = 'selected';
      if (!version && meta.dependencies?.[peer]) {
        const dependency = await resolve(peer, meta.dependencies[peer]);
        version = dependency.version; provider = 'declared_transitive';
      }
      const status = version ? (semver.satisfies(version, range) ? 'PASS' : 'FAIL') : (optional ? 'OPTIONAL_NOT_SELECTED' : 'MISSING');
      checks.push({ package: name, peer, required: range, provided: version || null, provider: version ? provider : null, status });
      if (status === 'MISSING' || status === 'FAIL') missing.push(checks.at(-1));
    }
  }
  const nodeIndex = await request('https://nodejs.org/dist/index.json');
  const node24 = nodeIndex.filter(item => item.lts && item.date <= '2026-10-09' && semver.satisfies(item.version, '24.x')).sort((a, b) => semver.rcompare(a.version, b.version))[0];
  const engineChecks = [...selected].filter(([, { meta }]) => meta.engines?.node).map(([name, { meta }]) => ({ package: name, required: meta.engines.node, candidate: node24.version, status: semver.satisfies(node24.version, meta.engines.node) ? 'PASS' : 'FAIL' }));
  const build = selected.get('expo-build-properties').meta;
  const buildFiles = await archive(build);
  const configSource = buildFiles.get('package/src/pluginConfig.ts')?.toString() || '';
  const androidSource = buildFiles.get('package/src/android.ts')?.toString() || '';
  const report = {
    checkedAt: new Date().toISOString(), timeZone: 'Asia/Shanghai', scope: 'published_metadata_and_source_only',
    expoVersion: expo.version, node24Candidate: node24.version, packageManager: 'pnpm@10.28.2',
    packages: [...selected].map(([name, { meta, scope, range }]) => ({ name, version: meta.version, scope, sdkOrCandidateRange: range, engines: meta.engines || {}, license: meta.license || null, source: registry + encodeURIComponent(name) + '/' + meta.version, tarball: meta.dist.tarball, integrity: meta.dist.integrity })),
    peerChecks: checks, engineChecks, problems: missing,
    buildPropertiesSource: { version: build.version, minSdkDeclaration: /minSdkVersion\??\s*:/.test(configSource), minSdkGradleMapping: androidSource.includes('android.minSdkVersion'), source: build.dist.tarball },
    checkedArchives: [{ name: expo.name, version: expo.version }, { name: build.name, version: build.version }],
    verification: { registryVersions: 'PASS', selectedPeers: missing.length ? 'FAIL' : 'PASS', nodeEngines: engineChecks.every(check => check.status === 'PASS') ? 'PASS' : 'FAIL', checkedArchiveIntegrity: 'PASS', dependencyInstall: 'NOT_RUN', nativeBuild: 'NOT_RUN', hermesAndroid: 'NOT_RUN', emulator: 'NOT_RUN', release: 'NOT_RUN' }
  };
  fs.writeFileSync(path.join(__dirname, '依赖元数据核查结果.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ expo: report.expoVersion, node: report.node24Candidate, packages: report.packages.length, peerProblems: missing, engines: report.verification.nodeEngines, minSdk: report.buildPropertiesSource }));
  if (missing.length || report.verification.nodeEngines !== 'PASS' || !report.buildPropertiesSource.minSdkDeclaration || !report.buildPropertiesSource.minSdkGradleMapping) process.exitCode = 1;
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
