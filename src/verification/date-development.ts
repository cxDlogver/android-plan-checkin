import { getCalendars } from 'expo-localization';
import { addDays, businessToday, date, dayMs, nextMonday, validZone } from '../domain/date';
import { DomainError } from '../domain/model';
import { initializeTimezone } from '../infrastructure/database/timezone';
import { loadFacts, persist } from '../infrastructure/database/executor';
import { verificationExecutor } from './runtime-development';
import { Projections } from '../application/projections';
import type { Snapshot } from '../domain/model';

const projections=new Projections();
let previousDays:unknown;
export function calendarProbe(snapshot:Snapshot){
  const view=projections.calendar(snapshot,'2026-10','2026-10-09');
  const result={today:view.today,zone:view.zone,dataRevision:view.dataRevision,sameCachedDays:view.days===previousDays};
  previousDays=view.days;
  return result;
}

export const dateExamples=[
  {rowId:'spring',zone:'America/New_York',day:'2026-03-08',next:'2026-03-09',hours:23},
  {rowId:'fall',zone:'America/New_York',day:'2026-11-01',next:'2026-11-02',hours:25},
  {rowId:'leap',zone:'Asia/Shanghai',day:'2028-02-28',next:'2028-02-29',hours:24},
  {rowId:'year',zone:'Asia/Shanghai',day:'2026-12-31',next:'2027-01-01',hours:24},
];
export function dateProbe(){
  let invalidCode:string|undefined;
  try{date('2026-02-30');}catch(error){invalidCode=error instanceof DomainError?error.code:String(error);}
  return {examples:dateExamples.map(row=>({...row,roundTrip:date(row.day,row.zone).toISODate(),actualNext:addDays(row.day,1,row.zone),actualHours:(dayMs(addDays(row.day,1,row.zone),row.zone)-dayMs(row.day,row.zone))/3600000})),invalidCode,monday:nextMonday('2026-10-12','Asia/Shanghai'),sunday:nextMonday('2026-10-11','Asia/Shanghai')};
}
export async function timezoneProbe(candidate:string|null,empty:boolean){
  if(candidate!==null&&typeof candidate!=='string')throw new Error('INVALID_CANDIDATE');
  const executor=verificationExecutor();
  return executor.queue(async tx=>{
    const original=await loadFacts(tx),deviceZone=getCalendars()[0]?.timeZone;
    try{
      if(empty)await executor.transaction(tx,async()=>{await tx.run("DELETE FROM app_meta WHERE key IN ('app_timezone','initialized_at_ms','data_revision')");});
      const before=await tx.all('SELECT * FROM app_meta ORDER BY key');
      let code='OK',zone:string|undefined,candidateReads=0;
      try{zone=await executor.transaction(tx,()=>initializeTimezone(tx,()=>{candidateReads++;return candidate;},Date.parse('2026-10-08T16:30:00Z')));}
      catch(error){code=error instanceof DomainError?error.code:String(error);}
      const after=await tx.all('SELECT * FROM app_meta ORDER BY key');
      let secondZone:string|undefined,secondCandidateReads=0;
      if(zone)secondZone=await executor.transaction(tx,()=>initializeTimezone(tx,()=>{secondCandidateReads++;return 'America/New_York';},Date.parse('2026-10-09T16:30:00Z')));
      const secondAfter=await tx.all('SELECT * FROM app_meta ORDER BY key');
      const data={candidate,empty,deviceZone,before,after,code,zone,candidateReads,secondZone,secondCandidateReads,secondAfter,firstToday:zone?businessToday(Date.parse('2026-10-08T16:30:00Z'),zone):null,valid:zone?validZone(zone):false,original};
      await executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),original));
      return {...data,restored:await loadFacts(tx)};
    }catch(error){await executor.transaction(tx,async()=>persist(tx,await loadFacts(tx),original));throw error;}
  });
}
