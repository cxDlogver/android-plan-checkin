export type BusinessDate = string;
export type PlanType = 'fixed' | 'weekly' | 'one_time';
export type Direction = 'do' | 'avoid';
export type CycleResult = 'success' | 'failure' | 'skip';
export type Outcome = 'completed' | 'failed' | 'cancelled';
export type EntryKind = 'ordinary' | 'backfill';
export type RuleKind = 'weekday_mask' | 'weekly_target' | 'end_on' | 'due_on';
export type Status = 'running' | 'paused' | 'archived';
export interface Plan { id: string; type: PlanType; direction: Direction; name: string; description: string; created_at_ms: number; created_on: BusinessDate; starts_on: BusinessDate; revision: number }
export interface Rule { id: string; plan_id: string; kind: RuleKind; effective_on: BusinessDate; revision: number; value_json: string; created_at_ms: number; cancelled_at_ms: number | null }
export interface LifecycleEvent { id: string; plan_id: string; kind: 'pause' | 'resume' | 'archive'; source_key: string; effective_on: BusinessDate; effective_at_ms: number; reason: 'user' | 'cycle_end' | 'one_time_terminal' | 'historical_terminal'; requested_at_ms: number; cancelled_at_ms: number | null }
export interface CycleRecord { id: string; plan_id: string; business_on: BusinessDate; result: CycleResult; note: string; entry_kind: EntryKind; submitted_at_ms: number; modified_at_ms: number | null; revision: number }
export interface OneTimeResult { id: string; plan_id: string; business_on: BusinessDate; outcome: Outcome; actual_completed_on: BusinessDate | null; due_rule_version_id: string; note: string; entry_kind: EntryKind; submitted_at_ms: number; modified_at_ms: number | null; revision: number }
export interface CycleOriginal { record_id: string; original_result: CycleResult; original_note: string }
export interface OneTimeOriginal { result_id: string; original_outcome: Outcome; original_note: string }
export interface Receipt { command_id: string; plan_id: string | null; kind: CommandKind; payload_digest: string | null; result_code: 'OK' | 'TARGET_REMOVED'; object_id: string | null; issued_at_ms: number; committed_at_ms: number; expires_at_ms: number }
export interface Meta { key: string; value: string }
export interface Facts { plans: Plan[]; rule_versions: Rule[]; lifecycle_events: LifecycleEvent[]; cycle_records: CycleRecord[]; one_time_results: OneTimeResult[]; cycle_record_originals: CycleOriginal[]; one_time_result_originals: OneTimeOriginal[]; command_receipts: Receipt[]; app_meta: Meta[] }
export interface Snapshot { facts: Facts; asOfMs: number; today: BusinessDate; zone: string; dataRevision: number }
export type CommandKind = 'CreatePlan' | 'SubmitCycleRecord' | 'ModifyCycleRecord' | 'SubmitOneTimeResult' | 'ModifyOneTimeResult' | 'EditPlan' | 'RequestPause' | 'RequestResume' | 'CancelPendingState' | 'ArchivePlan' | 'PermanentlyDeletePlan';
export interface Envelope { commandId: string; issuedAtMs: number; kind: CommandKind; payload: Record<string, unknown> }
export type ErrorCode = 'VALIDATION_FAILED' | 'DAY_CHANGED' | 'CONFIRMATION_STALE' | 'PLAN_CHANGED' | 'RECORD_CHANGED' | 'RECORD_EXISTS' | 'DATE_INELIGIBLE' | 'OLD_STAGE' | 'PAUSED' | 'ARCHIVED' | 'READ_ONLY' | 'TARGET_REMOVED' | 'COMMAND_ID_REUSED' | 'COMMAND_EXPIRED' | 'CLOCK_CHANGED' | 'STORAGE_FULL' | 'STORAGE_BUSY' | 'STORAGE_IO' | 'INIT_FAILED' | 'MIGRATION_FAILED' | 'SCHEMA_TOO_NEW';
export class DomainError extends Error { constructor(public code: ErrorCode, public fieldErrors?: Record<string, string>) { super(code); } }
export type CommandResult = {ok: true; code: 'OK'; objectId?: string; dataRevision: number; replayed: boolean} | {ok: false; code: ErrorCode; fieldErrors?: Record<string,string>};
export const emptyFacts = (): Facts => ({plans:[],rule_versions:[],lifecycle_events:[],cycle_records:[],one_time_results:[],cycle_record_originals:[],one_time_result_originals:[],command_receipts:[],app_meta:[]});
export const metaValue = (facts: Facts, key: string) => facts.app_meta.find(item=>item.key===key)?.value;
export function setMeta(facts: Facts,key: string,value: string) { const item=facts.app_meta.find(item=>item.key===key); if(item)item.value=value;else facts.app_meta.push({key,value}); }
