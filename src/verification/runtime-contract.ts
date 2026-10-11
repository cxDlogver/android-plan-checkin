import type { DatabaseExecutor } from '../infrastructure/database/executor';
import type { Envelope } from '../domain/model';
export declare function now():number;
export declare function beforeStorage(sql:string):void|Promise<void>;
export declare function afterUserCommit():void|Promise<void>;
export declare function observeUserCommand(envelope:Envelope):void;
export declare function attachExecutor(executor:DatabaseExecutor):void;
export declare function attachReadInitialization(callback:()=>Promise<void>):void;
export declare function settingsVersion(version:string|null,build:string|null):{version:string|null;build:string|null};
