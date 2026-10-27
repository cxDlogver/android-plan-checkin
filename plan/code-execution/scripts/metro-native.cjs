'use strict';
const path=require('node:path');const root=path.resolve(__dirname,'../../..'),config=require(path.join(root,'metro.config.cjs'));
// Evidence is not an application module; app sources and font resources remain watched.
const special=[92,94,36,46,42,43,63,40,41,91,93,123,125,124],escaped=[...root].map(c=>special.includes(c.charCodeAt(0))?String.fromCharCode(92)+c:c).join(''),separator='['+String.fromCharCode(92,92)+'/]';
config.resolver.blockList=[...(Array.isArray(config.resolver.blockList)?config.resolver.blockList:[config.resolver.blockList].filter(Boolean)),new RegExp(escaped+separator+'plan(?:'+separator+'.*)?$')];
module.exports=config;
