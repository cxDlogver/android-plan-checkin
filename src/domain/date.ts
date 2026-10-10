import { DateTime, IANAZone } from 'luxon';
import { DomainError } from './model';

export function validZone(zone: string) { return IANAZone.isValidZone(zone); }
export function date(value: string, zone = 'Asia/Shanghai') {
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!validZone(zone))throw new DomainError('VALIDATION_FAILED',{date:'请输入有效日期 YYYY-MM-DD'});
  const parsed=DateTime.fromISO(value,{zone}).startOf('day');
  if(!parsed.isValid||parsed.toISODate()!==value)throw new DomainError('VALIDATION_FAILED',{date:'日期不存在'});
  return parsed;
}
export const businessToday=(now: number,zone: string)=>DateTime.fromMillis(now,{zone}).toISODate()!;
export const dayMs=(value: string,zone: string)=>date(value,zone).toMillis();
export const addDays=(value: string,days: number,zone: string)=>date(value,zone).plus({days}).toISODate()!;
export const weekday=(value: string,zone: string)=>date(value,zone).weekday;
export const monday=(value: string,zone: string)=>addDays(value,1-weekday(value,zone),zone);
export const nextMonday=(value: string,zone: string)=>addDays(monday(value,zone),7,zone);
export function daysBetween(first: string,last: string,zone: string){const result:string[]=[];for(let current=first;current<=last;current=addDays(current,1,zone))result.push(current);return result;}
export const monthGrid=(month: string,zone: string)=>{const start=date(`${month}-01`,zone);const first=addDays(start.toISODate()!,1-start.weekday,zone);return Array.from({length:42},(_,i)=>addDays(first,i,zone));};
export const shiftMonth=(month: string,offset: number,zone: string)=>date(`${month}-01`,zone).plus({months:offset}).toFormat('yyyy-MM');
export const formatDate=(value: string,zone: string)=>date(value,zone).setLocale('zh-CN').toFormat('M月d日 cccc');
export const formatInstant=(ms: number,zone: string)=>DateTime.fromMillis(ms,{zone}).toFormat('yyyy-MM-dd HH:mm');
