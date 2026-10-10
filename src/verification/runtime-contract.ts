import type { DatabaseExecutor } from '../infrastructure/database/executor';
export declare function now():number;
export declare function beforeStorage(sql:string):void;
export declare function afterUserCommit():void;
export declare function attachExecutor(executor:DatabaseExecutor):void;
