'use strict';
module.exports=options=>require('./accept-'+options.taskIds.at(-1).toLowerCase()+'.cjs')(options);
