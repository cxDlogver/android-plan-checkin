-- Schema 2 strengthens existing immutable facts without changing table layouts or stored rows.
CREATE TRIGGER immutable_plans
BEFORE UPDATE ON plans
WHEN OLD.id IS NOT NEW.id OR OLD.type IS NOT NEW.type OR OLD.direction IS NOT NEW.direction OR OLD.created_at_ms IS NOT NEW.created_at_ms OR OLD.created_on IS NOT NEW.created_on OR OLD.starts_on IS NOT NEW.starts_on
BEGIN
  SELECT RAISE(ABORT, 'immutable plans');
END;

CREATE TRIGGER immutable_cycle_records
BEFORE UPDATE ON cycle_records
WHEN OLD.id IS NOT NEW.id OR OLD.plan_id IS NOT NEW.plan_id OR OLD.business_on IS NOT NEW.business_on OR OLD.entry_kind IS NOT NEW.entry_kind OR OLD.submitted_at_ms IS NOT NEW.submitted_at_ms
BEGIN
  SELECT RAISE(ABORT, 'immutable cycle_records');
END;

CREATE TRIGGER immutable_one_time_results
BEFORE UPDATE ON one_time_results
WHEN OLD.id IS NOT NEW.id OR OLD.plan_id IS NOT NEW.plan_id OR OLD.business_on IS NOT NEW.business_on OR OLD.entry_kind IS NOT NEW.entry_kind OR OLD.submitted_at_ms IS NOT NEW.submitted_at_ms OR OLD.due_rule_version_id IS NOT NEW.due_rule_version_id
BEGIN
  SELECT RAISE(ABORT, 'immutable one_time_results');
END;

CREATE TRIGGER immutable_cycle_record_originals
BEFORE UPDATE ON cycle_record_originals
WHEN OLD.record_id IS NOT NEW.record_id OR OLD.original_result IS NOT NEW.original_result OR OLD.original_note IS NOT NEW.original_note
BEGIN
  SELECT RAISE(ABORT, 'immutable cycle_record_originals');
END;

CREATE TRIGGER immutable_one_time_result_originals
BEFORE UPDATE ON one_time_result_originals
WHEN OLD.result_id IS NOT NEW.result_id OR OLD.original_outcome IS NOT NEW.original_outcome OR OLD.original_note IS NOT NEW.original_note
BEGIN
  SELECT RAISE(ABORT, 'immutable one_time_result_originals');
END;

CREATE TRIGGER immutable_rule_versions
BEFORE UPDATE ON rule_versions
WHEN OLD.id IS NOT NEW.id OR OLD.plan_id IS NOT NEW.plan_id OR OLD.kind IS NOT NEW.kind OR OLD.effective_on IS NOT NEW.effective_on OR OLD.revision IS NOT NEW.revision OR OLD.value_json IS NOT NEW.value_json OR OLD.created_at_ms IS NOT NEW.created_at_ms
BEGIN
  SELECT RAISE(ABORT, 'immutable rule_versions');
END;

CREATE TRIGGER immutable_lifecycle_events
BEFORE UPDATE ON lifecycle_events
WHEN OLD.id IS NOT NEW.id OR OLD.plan_id IS NOT NEW.plan_id OR OLD.kind IS NOT NEW.kind OR OLD.source_key IS NOT NEW.source_key OR OLD.effective_on IS NOT NEW.effective_on OR OLD.effective_at_ms IS NOT NEW.effective_at_ms OR OLD.reason IS NOT NEW.reason OR OLD.requested_at_ms IS NOT NEW.requested_at_ms
BEGIN
  SELECT RAISE(ABORT, 'immutable lifecycle_events');
END;
