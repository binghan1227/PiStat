import json
import sqlite3
import time

import pytest

from pistat.db import (
    METRIC_ALLOWLIST,
    init_db,
    insert,
    prune,
    query_latest,
    query_range,
)


def test_init_db_creates_table(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_init_db_idempotent(tmp_db):
    # Calling init_db again on an already-initialised DB must not raise
    init_db(tmp_db)


def test_insert_and_query_latest(tmp_db):
    ts = time.time()
    insert(tmp_db, {"timestamp": ts, "cpu_percent": 42.0})
    row = query_latest(tmp_db)
    assert row is not None
    assert row["cpu_percent"] == pytest.approx(42.0)


def test_query_latest_empty_db(tmp_db):
    result = query_latest(tmp_db)
    assert result is None


def test_insert_preserves_cpu_percent(tmp_db):
    insert(tmp_db, {"timestamp": time.time(), "cpu_percent": 77.5})
    row = query_latest(tmp_db)
    assert row["cpu_percent"] == pytest.approx(77.5)


def test_insert_cpu_per_core_json(tmp_db):
    cores = [10.0, 20.0, 30.0, 40.0]
    insert(tmp_db, {"timestamp": time.time(), "cpu_per_core": json.dumps(cores)})
    row = query_latest(tmp_db)
    assert isinstance(row["cpu_per_core"], list)
    assert row["cpu_per_core"] == pytest.approx(cores)


def test_query_range_valid_metric(tmp_db):
    ts = time.time()
    insert(tmp_db, {"timestamp": ts, "cpu_percent": 55.0})
    rows = query_range(tmp_db, ts - 1, "cpu_percent")
    assert len(rows) == 1
    assert rows[0][1] == pytest.approx(55.0)


def test_query_range_invalid_metric_raises(tmp_db):
    with pytest.raises(ValueError):
        query_range(tmp_db, time.time() - 3600, "not_a_real_metric")


def test_query_range_respects_since_ts(tmp_db):
    old_ts = time.time() - 7200
    new_ts = time.time()
    insert(tmp_db, {"timestamp": old_ts, "cpu_percent": 10.0})
    insert(tmp_db, {"timestamp": new_ts, "cpu_percent": 20.0})
    rows = query_range(tmp_db, time.time() - 3600, "cpu_percent")
    assert len(rows) == 1
    assert rows[0][1] == pytest.approx(20.0)


def test_prune_removes_old_rows(tmp_db):
    old_ts = time.time() - 100 * 86400  # 100 days ago
    insert(tmp_db, {"timestamp": old_ts, "cpu_percent": 5.0})
    prune(tmp_db, retention_days=7)
    rows = query_range(tmp_db, old_ts - 1, "cpu_percent")
    assert len(rows) == 0


def test_prune_keeps_recent_rows(tmp_db):
    recent_ts = time.time() - 3600  # 1 hour ago
    insert(tmp_db, {"timestamp": recent_ts, "cpu_percent": 99.0})
    prune(tmp_db, retention_days=7)
    row = query_latest(tmp_db)
    assert row is not None
    assert row["cpu_percent"] == pytest.approx(99.0)


def test_prune_empty_db(tmp_db):
    prune(tmp_db, retention_days=7)  # must not raise


def test_insert_partial_row(tmp_db):
    insert(tmp_db, {"timestamp": time.time(), "cpu_percent": 33.0})
    row = query_latest(tmp_db)
    assert row["mem_used"] is None
    assert row["disk_used"] is None


def test_allowlist_contains_expected_metrics():
    assert "cpu_percent" in METRIC_ALLOWLIST
    assert "mem_percent" in METRIC_ALLOWLIST
    assert "cpu_temp" in METRIC_ALLOWLIST
    assert "uptime_seconds" in METRIC_ALLOWLIST
    # cpu_per_core is a JSON array, not a scalar — excluded from allowlist
    assert "cpu_per_core" not in METRIC_ALLOWLIST


def test_multiple_inserts_query_latest_returns_newest(tmp_db):
    t1 = time.time() - 10
    t2 = time.time()
    insert(tmp_db, {"timestamp": t1, "cpu_percent": 11.0})
    insert(tmp_db, {"timestamp": t2, "cpu_percent": 99.0})
    row = query_latest(tmp_db)
    assert row["cpu_percent"] == pytest.approx(99.0)
