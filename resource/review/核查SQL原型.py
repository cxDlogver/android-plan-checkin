"""Review DDL audit using host SQLite; this is not an Android application test."""
import hashlib
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
DDL = REVIEW.parent / "technical" / "schema-v1.sql"
SQL = DDL.read_text(encoding="utf-8")
RESULTS = []


def statements(script):
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if pending.strip():
        raise ValueError("Incomplete SQL statement")


def create_db(directory, name):
    conn = sqlite3.connect(str(directory / (name + ".db")), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("BEGIN")
    for statement in statements(SQL):
        conn.execute(statement)
    conn.execute("COMMIT")
    return conn


def plan(conn, pid="p", kind="fixed"):
    conn.execute("INSERT INTO plans VALUES (?, ?, 'do', 'sample', '', 1, '2026-10-09', '2026-10-09', 1)", (pid, kind))


def rule(conn, rid="due", pid="p", kind="due_on", value='{"dueOn":"2026-10-10"}'):
    conn.execute("INSERT INTO rule_versions VALUES (?, ?, ?, '2026-10-09', 1, ?, 1, NULL)", (rid, pid, kind, value))


def cycle(conn, rid="r", pid="p"):
    conn.execute("INSERT INTO cycle_records VALUES (?, ?, '2026-10-09', 'success', 'note', 'ordinary', 1, NULL, 1)", (rid, pid))


def once(conn, rid="r", pid="p", due="due"):
    conn.execute("INSERT INTO one_time_results VALUES (?, ?, '2026-10-09', 'completed', '2026-10-09', ?, 'note', 'ordinary', 1, NULL, 1)", (rid, pid, due))


def rejects(operation):
    try:
        operation()
    except sqlite3.DatabaseError:
        return
    raise AssertionError("Expected SQLite rejection")


def audit(name, operation, directory):
    conn = None
    try:
        conn = create_db(directory, name)
        operation(conn)
        RESULTS.append({"id": name, "status": "PASS"})
    except Exception as error:
        RESULTS.append({"id": name, "status": "FAIL", "error": str(error)})
    finally:
        if conn:
            conn.close()


def parameters(conn):
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    tables = conn.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall()
    assert len(tables) == 9


def unique_cycle(conn):
    plan(conn)
    cycle(conn)
    rejects(lambda: cycle(conn, "second"))
    assert conn.execute("SELECT count(*) FROM cycle_records").fetchone()[0] == 1


def unique_once(conn):
    plan(conn, kind="one_time")
    rule(conn)
    once(conn)
    rejects(lambda: once(conn, "second"))


def composite_fk(conn):
    plan(conn, "p", "one_time")
    plan(conn, "other", "one_time")
    rule(conn, pid="other")
    conn.execute("BEGIN")
    once(conn)
    rejects(lambda: conn.execute("COMMIT"))
    conn.execute("ROLLBACK")
    assert conn.execute("SELECT count(*) FROM one_time_results").fetchone()[0] == 0


def cascade_delete(conn):
    plan(conn, kind="one_time")
    rule(conn)
    once(conn)
    conn.execute("INSERT INTO one_time_result_originals VALUES ('r','failed','old note')")
    conn.execute("INSERT INTO command_receipts VALUES ('c','p','CreatePlan',?,'OK','p',1,2,604800001)", ("a" * 64,))
    conn.execute("BEGIN")
    conn.execute("UPDATE command_receipts SET result_code='TARGET_REMOVED', plan_id=NULL, object_id=NULL, payload_digest=NULL WHERE plan_id='p'")
    conn.execute("DELETE FROM plans WHERE id='p'")
    conn.execute("COMMIT")
    for table in ("plans", "rule_versions", "one_time_results", "one_time_result_originals"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert conn.execute("SELECT result_code,plan_id,object_id,payload_digest FROM command_receipts").fetchone() == ("TARGET_REMOVED", None, None, None)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def cycle_cascade(conn):
    plan(conn)
    cycle(conn)
    conn.execute("INSERT INTO cycle_record_originals VALUES ('r','failure','old')")
    conn.execute("INSERT INTO lifecycle_events VALUES ('e','p','archive','command:c','2026-10-09',2,'user',2,NULL)")
    conn.execute("DELETE FROM plans WHERE id='p'")
    for table in ("cycle_records", "cycle_record_originals", "lifecycle_events"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def rollback_write(conn):
    plan(conn)
    conn.execute("BEGIN")
    cycle(conn)
    rejects(lambda: cycle(conn, "duplicate"))
    conn.execute("ROLLBACK")
    assert conn.execute("SELECT count(*) FROM cycle_records").fetchone()[0] == 0


def rollback_migrations(conn):
    plan(conn)
    conn.execute("BEGIN")
    conn.execute("ALTER TABLE plans ADD COLUMN temporary_column TEXT")
    conn.execute("UPDATE plans SET name='changed'")
    conn.execute("PRAGMA user_version=2")
    rejects(lambda: conn.execute("ALTER TABLE nonexistent ADD COLUMN broken TEXT"))
    conn.execute("ROLLBACK")
    assert "temporary_column" not in [row[1] for row in conn.execute("PRAGMA table_info(plans)")]
    assert conn.execute("SELECT name FROM plans").fetchone()[0] == "sample"
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def checks(conn):
    plan(conn)
    for value in ('{}', '{"weeklyTarget":0}', '{"weeklyTarget":8}', '{"weeklyTarget":3.5}', '{"weeklyTarget":"3"}'):
        rejects(lambda v=value: rule(conn, kind="weekly_target", value=v))
    rule(conn, kind="weekly_target", value='{"weeklyTarget":3}')
    rejects(lambda: conn.execute("UPDATE plans SET type='invalid'"))
    rejects(lambda: conn.execute("UPDATE plans SET revision=0"))
    rejects(lambda: conn.execute("UPDATE plans SET created_at_ms='not integer'"))


def null_and_date(conn):
    rejects(lambda: conn.execute("INSERT INTO app_meta VALUES (NULL,'x')"))
    plan(conn)
    rejects(lambda: conn.execute("UPDATE plans SET starts_on='2026/10/09'"))
    # SQL date-shape validation deliberately does not implement calendar validity.
    conn.execute("UPDATE plans SET starts_on='2026-99-99'")
    assert conn.execute("SELECT starts_on FROM plans").fetchone()[0] == "2026-99-99"


def outcome_checks(conn):
    plan(conn, kind="one_time")
    rule(conn)
    once(conn)
    rejects(lambda: conn.execute("UPDATE one_time_results SET outcome='failed'"))
    conn.execute("UPDATE one_time_results SET outcome='failed', actual_completed_on=NULL")
    rejects(lambda: conn.execute("UPDATE one_time_results SET entry_kind='backfill'"))


def originals(conn):
    plan(conn)
    cycle(conn)
    conn.execute("INSERT INTO cycle_record_originals VALUES ('r','success','first') ON CONFLICT DO NOTHING")
    conn.execute("INSERT INTO cycle_record_originals VALUES ('r','failure','later') ON CONFLICT DO NOTHING")
    assert conn.execute("SELECT original_result,original_note FROM cycle_record_originals").fetchone() == ("success", "first")


def receipt_checks(conn):
    rejects(lambda: conn.execute("INSERT INTO command_receipts VALUES ('c',NULL,'CreatePlan','digest','TARGET_REMOVED',NULL,1,2,604800001)"))
    conn.execute("INSERT INTO command_receipts VALUES ('c',NULL,'CreatePlan',NULL,'TARGET_REMOVED',NULL,1,2,604800001)")
    rejects(lambda: conn.execute("INSERT INTO command_receipts SELECT * FROM command_receipts"))


with tempfile.TemporaryDirectory(prefix="plan-checkin-sql-review-") as tmp:
    directory = Path(tmp).resolve()
    # Verify the automatically cleaned test directory is under the system temp root.
    directory.relative_to(Path(tempfile.gettempdir()).resolve())
    for name, operation in (
        ("DDL_AND_PRAGMAS", parameters), ("UNIQUE_CYCLE", unique_cycle),
        ("UNIQUE_ONE_TIME", unique_once), ("DEFERRED_COMPOSITE_FK", composite_fk),
        ("ONE_TIME_CASCADE_AND_TOMBSTONE", cascade_delete), ("CYCLE_CASCADE", cycle_cascade),
        ("WRITE_ROLLBACK", rollback_write), ("ALL_MIGRATIONS_ROLLBACK", rollback_migrations),
        ("RULE_ENUM_STRICT_CHECKS", checks), ("DATE_SHAPE_BOUNDARY", null_and_date),
        ("ONE_TIME_OUTCOME_CHECKS", outcome_checks), ("FIRST_ORIGINAL_ONLY", originals),
        ("RECEIPT_CONSTRAINTS", receipt_checks),
    ):
        audit(name, operation, directory)

with sqlite3.connect(":memory:") as info:
    source_id = info.execute("SELECT sqlite_source_id()").fetchone()[0]
report = {
    "date": datetime.now(timezone.utc).isoformat(),
    "scope": "host_sqlite_review_prototype",
    "schemaFile": "technical/schema-v1.sql",
    "schemaSha256": hashlib.sha256(DDL.read_bytes()).hexdigest(),
    "hostSQLiteVersion": sqlite3.sqlite_version,
    "hostSQLiteSourceId": source_id,
    "status": "PASS" if all(x["status"] == "PASS" for x in RESULTS) else "FAIL",
    "cases": RESULTS,
    "limitations": ["SQL date checks validate shape only; domain must reject impossible dates", "Cross-row plan type, stage, readonly and rule-kind permissions require application validation"],
    "androidExpoSQLite": "NOT_RUN",
    "applicationImplementation": "NOT_RUN",
}
(REVIEW / "SQL原型核查结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "hostSQLiteVersion": report["hostSQLiteVersion"], "cases": len(RESULTS), "failures": [x for x in RESULTS if x["status"] != "PASS"], "androidExpoSQLite": "NOT_RUN"}, ensure_ascii=False))
raise SystemExit(0 if report["status"] == "PASS" else 1)
