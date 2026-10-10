const assert=require('node:assert/strict'),fs=require('node:fs');
const {signingSource}=require('../plugins/with-release-signing.cjs');
const input=fs.readFileSync('android/app/build.gradle','utf8'),output=signingSource(input);
assert.equal(signingSource(output),output);
assert.match(output,/signingConfig signingConfigs\.release/);
assert.match(output,/Release signing environment is required/);
assert.match(output,/rootDir\.parentFile\.canonicalFile/);
assert.match(output,/debug\s*\{\s*signingConfig signingConfigs\.debug/);
console.log('PASS release signing template: external environment, no debug fallback, idempotent generation');
