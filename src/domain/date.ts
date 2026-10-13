import { DateTime, IANAZone } from 'luxon';
import { DomainError } from './model';

const zones=new Map<string,boolean>(), dates=new Map<string,DateTime>(), additions=new Map<string,string|null>();
function remember<T>(cache:Map<string,T>,key:string,value:T,limit:number){cache.delete(key);cache.set(key,value);if(cache.size>limit)cache.delete(cache.keys().next().value!);return value;}
export function validZone(zone: string) { const cached=zones.get(zone);return cached===undefined?remember(zones,zone,IANAZone.isValidZone(zone),32):cached; }
export function date(value: string, zone = 'Asia/Shanghai') {
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!validZone(zone))throw new DomainError('VALIDATION_FAILED',{date:'请输入有效日期 YYYY-MM-DD'});
  const key=zone+'|'+value,cached=dates.get(key);if(cached)return cached;
  const parsed=DateTime.fromISO(value,{zone}).startOf('day');
  if(!parsed.isValid||parsed.toISODate()!==value)throw new DomainError('VALIDATION_FAILED',{date:'日期不存在'});
  return remember(dates,key,parsed,2048);
}
export const businessToday=(now: number,zone: string)=>DateTime.fromMillis(now,{zone}).toISODate()!;
export const dayMs=(value: string,zone: string)=>date(value,zone).toMillis();
export const addDays=(value: string,days: number,zone: string)=>{const parsed=date(value,zone),key=zone+'|'+value+'|'+days;if(additions.has(key))return additions.get(key)!;return remember(additions,key,parsed.plus({days}).toISODate(),4096)!;};
export const weekday=(value: string,zone: string)=>date(value,zone).weekday;
export const monday=(value: string,zone: string)=>addDays(value,1-weekday(value,zone),zone);
export const nextMonday=(value: string,zone: string)=>addDays(monday(value,zone),7,zone);
export function daysBetween(first: string,last: string,zone: string){const result:string[]=[];for(let current=first;current<=last;current=addDays(current,1,zone))result.push(current);return result;}
export const monthGrid=(month: string,zone: string)=>{const start=date(`${month}-01`,zone);const first=addDays(start.toISODate()!,1-start.weekday,zone);return Array.from({length:42},(_,i)=>addDays(first,i,zone));};
export const shiftMonth=(month: string,offset: number,zone: string)=>date(`${month}-01`,zone).plus({months:offset}).toFormat('yyyy-MM');
export const formatDate=(value: string,zone: string)=>{const day=date(value,zone);return `${day.month}月${day.day}日 ${['星期一','星期二','星期三','星期四','星期五','星期六','星期日'][day.weekday-1]}`;};
export const formatInstant=(ms: number,zone: string)=>DateTime.fromMillis(ms,{zone}).toFormat('yyyy-MM-dd HH:mm');
