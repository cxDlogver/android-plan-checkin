-- Technical review prototype only; not an installed application migration.
-- Connection PRAGMAs are set outside the migration transaction by the executor.
-- Execute all pending migrations in one transaction; set user_version last.

CREATE TABLE app_meta (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
) STRICT;

CREATE TABLE plans (
  id TEXT PRIMARY KEY NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('fixed', 'weekly', 'one_time')),
  direction TEXT NOT NULL CHECK (direction IN ('do', 'avoid')),
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
  created_on TEXT NOT NULL CHECK (created_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  starts_on TEXT NOT NULL CHECK (starts_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  CHECK (starts_on >= created_on),
  CHECK (type <> 'one_time' OR (direction = 'do' AND starts_on = created_on))
) STRICT;

CREATE TABLE rule_versions (
  id TEXT PRIMARY KEY NOT NULL,
  plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('weekday_mask', 'weekly_target', 'end_on', 'due_on')),
  effective_on TEXT NOT NULL CHECK (effective_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  revision INTEGER NOT NULL CHECK (revision >= 1),
  value_json TEXT NOT NULL CHECK (json_valid(value_json)),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
  cancelled_at_ms INTEGER CHECK (cancelled_at_ms >= created_at_ms),
  UNIQUE (plan_id, id),
  UNIQUE (plan_id, kind, revision),
  CHECK (json_type(value_json) = 'object'),
  CHECK (CASE kind
    WHEN 'weekday_mask' THEN coalesce(json_type(value_json, '$.weekdayMask') = 'integer' AND json_extract(value_json, '$.weekdayMask') BETWEEN 1 AND 127, 0)
    WHEN 'weekly_target' THEN coalesce(json_type(value_json, '$.weeklyTarget') = 'integer' AND json_extract(value_json, '$.weeklyTarget') BETWEEN 1 AND 7, 0)
    WHEN 'end_on' THEN coalesce(json_type(value_json, '$.endOn') = 'null' OR (json_type(value_json, '$.endOn') = 'text' AND json_extract(value_json, '$.endOn') GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'), 0)
    WHEN 'due_on' THEN coalesce(json_type(value_json, '$.dueOn') = 'text' AND json_extract(value_json, '$.dueOn') GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]', 0)
    ELSE 0 END)
) STRICT;

CREATE TABLE lifecycle_events (
  id TEXT PRIMARY KEY NOT NULL,
  plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('pause', 'resume', 'archive')),
  source_key TEXT NOT NULL,
  effective_on TEXT NOT NULL CHECK (effective_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  effective_at_ms INTEGER NOT NULL CHECK (effective_at_ms >= 0),
  reason TEXT NOT NULL CHECK (reason IN ('user', 'cycle_end', 'one_time_terminal', 'historical_terminal')),
  requested_at_ms INTEGER NOT NULL CHECK (requested_at_ms >= 0),
  cancelled_at_ms INTEGER CHECK (cancelled_at_ms >= requested_at_ms),
  UNIQUE (plan_id, source_key),
  CHECK (kind = 'archive' OR reason = 'user')
) STRICT;

CREATE TABLE cycle_records (
  id TEXT PRIMARY KEY NOT NULL,
  plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  business_on TEXT NOT NULL CHECK (business_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  result TEXT NOT NULL CHECK (result IN ('success', 'failure', 'skip')),
  note TEXT NOT NULL DEFAULT '',
  entry_kind TEXT NOT NULL CHECK (entry_kind IN ('ordinary', 'backfill')),
  submitted_at_ms INTEGER NOT NULL CHECK (submitted_at_ms >= 0),
  modified_at_ms INTEGER CHECK (modified_at_ms >= submitted_at_ms),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  UNIQUE (plan_id, business_on)
) STRICT;

CREATE TABLE one_time_results (
  id TEXT PRIMARY KEY NOT NULL,
  plan_id TEXT NOT NULL UNIQUE REFERENCES plans(id) ON DELETE CASCADE,
  business_on TEXT NOT NULL CHECK (business_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  outcome TEXT NOT NULL CHECK (outcome IN ('completed', 'failed', 'cancelled')),
  actual_completed_on TEXT,
  due_rule_version_id TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  entry_kind TEXT NOT NULL CHECK (entry_kind IN ('ordinary', 'backfill')),
  submitted_at_ms INTEGER NOT NULL CHECK (submitted_at_ms >= 0),
  modified_at_ms INTEGER CHECK (modified_at_ms >= submitted_at_ms),
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  FOREIGN KEY (plan_id, due_rule_version_id) REFERENCES rule_versions(plan_id, id)
    ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
  CHECK ((outcome = 'completed' AND actual_completed_on IS NOT NULL AND actual_completed_on = business_on)
    OR (outcome <> 'completed' AND actual_completed_on IS NULL)),
  CHECK (entry_kind <> 'backfill' OR outcome = 'completed')
) STRICT;

CREATE TABLE cycle_record_originals (
  record_id TEXT PRIMARY KEY NOT NULL REFERENCES cycle_records(id) ON DELETE CASCADE,
  original_result TEXT NOT NULL CHECK (original_result IN ('success', 'failure', 'skip')),
  original_note TEXT NOT NULL
) STRICT;

CREATE TABLE one_time_result_originals (
  result_id TEXT PRIMARY KEY NOT NULL REFERENCES one_time_results(id) ON DELETE CASCADE,
  original_outcome TEXT NOT NULL CHECK (original_outcome IN ('completed', 'failed', 'cancelled')),
  original_note TEXT NOT NULL
) STRICT;

CREATE TABLE command_receipts (
  command_id TEXT PRIMARY KEY NOT NULL,
  plan_id TEXT REFERENCES plans(id) ON DELETE SET NULL,
  kind TEXT NOT NULL CHECK (kind IN ('CreatePlan', 'SubmitCycleRecord', 'ModifyCycleRecord', 'SubmitOneTimeResult', 'ModifyOneTimeResult', 'EditPlan', 'RequestPause', 'RequestResume', 'CancelPendingState', 'ArchivePlan', 'PermanentlyDeletePlan')),
  payload_digest TEXT,
  result_code TEXT NOT NULL CHECK (result_code IN ('OK', 'TARGET_REMOVED')),
  object_id TEXT,
  issued_at_ms INTEGER NOT NULL CHECK (issued_at_ms >= 0),
  committed_at_ms INTEGER NOT NULL CHECK (committed_at_ms >= 0),
  expires_at_ms INTEGER NOT NULL CHECK (expires_at_ms = issued_at_ms + 604800000),
  CHECK ((result_code = 'OK' AND payload_digest IS NOT NULL AND length(payload_digest) = 64)
    OR (result_code = 'TARGET_REMOVED' AND plan_id IS NULL AND object_id IS NULL AND payload_digest IS NULL))
) STRICT;

CREATE INDEX idx_plans_order ON plans(created_at_ms, id);
CREATE INDEX idx_rules_resolve ON rule_versions(plan_id, kind, effective_on, revision);
CREATE INDEX idx_lifecycle_resolve ON lifecycle_events(plan_id, effective_at_ms, requested_at_ms, id);
CREATE INDEX idx_cycle_calendar ON cycle_records(business_on, plan_id);
CREATE INDEX idx_once_calendar ON one_time_results(business_on, plan_id);
CREATE INDEX idx_receipts_plan ON command_receipts(plan_id);
CREATE INDEX idx_receipts_expiry ON command_receipts(expires_at_ms);

PRAGMA user_version = 1;
