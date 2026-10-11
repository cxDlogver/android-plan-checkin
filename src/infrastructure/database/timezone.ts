import { DomainError } from '../../domain/model';
import { validZone } from '../../domain/date';
import type { Tx } from './executor';

// Called inside the executor's initialization transaction. The device is read only
// for a database that has never stored a business zone.
export async function initializeTimezone(tx:Tx,candidate:()=>string|null|undefined,instant:number){
  const stored=await tx.first<{value:string}>("SELECT value FROM app_meta WHERE key='app_timezone'");
  if(stored){if(!validZone(stored.value))throw new DomainError('INIT_FAILED');return stored.value;}
  const zone=candidate();
  if(!zone||!validZone(zone))throw new DomainError('INIT_FAILED');
  await tx.run('INSERT INTO app_meta(key,value) VALUES (?,?),(?,?),(?,?)',['app_timezone',zone,'initialized_at_ms',String(instant),'data_revision','0']);
  return zone;
}
