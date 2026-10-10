const {registerHooks}=require('node:module');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const adapter=pathToFileURL(path.resolve('tests/integration/host-adapter.cjs')).href;
registerHooks({resolve(specifier,context,next){return ['expo-sqlite','expo-localization','expo-crypto','@verification/runtime'].includes(specifier)?{url:adapter,shortCircuit:true}:next(specifier,context);}});
