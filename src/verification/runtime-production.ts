export const now=()=>Date.now();
export const beforeStorage=(_sql:string):void|Promise<void>=>{};
export const afterUserCommit=():void|Promise<void>=>{};
export const observeUserCommand=(_envelope:unknown)=>{};
export const attachExecutor=(_executor:unknown)=>{};
export const attachReadInitialization=(_callback:()=>Promise<void>)=>{};
export const settingsVersion=(version:string|null,build:string|null)=>({version,build});
