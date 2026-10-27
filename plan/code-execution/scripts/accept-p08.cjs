'use strict';
module.exports=async options=>{if(options.mode==='unit'||options.args.includes('--scope-only'))return require('./p08-runtime.cjs')(options);return require('./p08-native.cjs')(options);};
