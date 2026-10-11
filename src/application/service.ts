import * as Crypto from 'expo-crypto';
import { now, afterUserCommit, observeUserCommand, attachExecutor } from '@verification/runtime';
import { DatabaseExecutor, loadFacts, persist, Tx } from '../infrastructure/database/executor';
import { applyCommand, canonical, normalizeEnvelope, receiptResult, reconcile } from '../domain/commands';
import { CommandResult, DomainError, Envelope, Facts, Snapshot, metaValue } from '../domain/model';
import { businessToday } from '../domain/date';

function storageCode(error:unknown){if(error instanceof DomainError)return error;const message=String(error);return new DomainError(/SQLITE_FULL|disk.*full/i.test(message)?'STORAGE_FULL':/SQLITE_BUSY|database.*locked/i.test(message)?'STORAGE_BUSY':'STORAGE_IO');}
export class AppService {
  constructor(private executor:DatabaseExecutor,private clock:()=>number=now){}
  private async reconciled(tx:Tx,now:number){const before=await loadFacts(tx),zone=metaValue(before,'app_timezone')!;const result=reconcile(before,now,zone,Crypto.randomUUID);if(result.changed)await this.executor.transaction(tx,()=>persist(tx,before,result.facts));return result.facts;}
  async snapshot():Promise<Snapshot>{return this.executor.queue(async tx=>{const now=this.clock();await this.reconciled(tx,now);return this.executor.transaction(tx,async()=>{const facts=await loadFacts(tx),zone=metaValue(facts,'app_timezone')!;return {facts,zone,today:businessToday(now,zone),asOfMs:now,dataRevision:Number(metaValue(facts,'data_revision')||0)};},true);});}
  async execute(input:Envelope):Promise<CommandResult>{
    try {
      const envelope=normalizeEnvelope(input);observeUserCommand(envelope);const digest=await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256,canonical(envelope));
      return await this.executor.queue(async tx=>{
        const now=this.clock(),receipt=await tx.first<Facts['command_receipts'][number]>('SELECT * FROM command_receipts WHERE command_id=?',[envelope.commandId]);
        const replay=receiptResult(receipt||undefined,envelope,digest,now);
        if(replay!==null){const current=await tx.first<{value:string}>("SELECT value FROM app_meta WHERE key='data_revision'");return {ok:true,code:'OK',objectId:replay,dataRevision:Number(current?.value||0),replayed:true};}
        await this.reconciled(tx,now);
        const committed=await this.executor.transaction<CommandResult>(tx,async()=>{
          const before=await loadFacts(tx),zone=metaValue(before,'app_timezone')!;
          const result=applyCommand(before,envelope,now,zone,Crypto.randomUUID),deleted=envelope.kind==='PermanentlyDeletePlan';
          result.facts.command_receipts.push({command_id:envelope.commandId,plan_id:deleted?null:envelope.payload.planId as string,kind:envelope.kind,payload_digest:deleted?null:digest,result_code:deleted?'TARGET_REMOVED':'OK',object_id:deleted?null:result.objectId,issued_at_ms:envelope.issuedAtMs,committed_at_ms:now,expires_at_ms:envelope.issuedAtMs+604800000});
          await persist(tx,before,result.facts);
          return {ok:true,code:'OK',objectId:result.objectId,dataRevision:Number(metaValue(result.facts,'data_revision')||0),replayed:false};
        });
        const gate=afterUserCommit();if(gate)await gate;return committed;
      });
    }catch(error){const failure=storageCode(error);return {ok:false,code:failure.code,fieldErrors:failure.fieldErrors};}
  }
  async cleanReceipts(){return this.executor.queue(async tx=>{const now=this.clock();await tx.run('DELETE FROM command_receipts WHERE command_id IN (SELECT command_id FROM command_receipts WHERE expires_at_ms<=? ORDER BY expires_at_ms LIMIT 200)',[now]);});}
  async diagnostics(){return this.executor.diagnostics();}
}
let startup:Promise<AppService>|undefined;
export function bootstrap(){startup??=DatabaseExecutor.open().then(async executor=>{try{attachExecutor(executor);const service=new AppService(executor);await service.snapshot();await service.cleanReceipts();return service;}catch(error){await executor.close();throw error;}}).catch(error=>{startup=undefined;throw error;});return startup;}
