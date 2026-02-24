import json
import sqlite3
import time

METRIC_ALLOWLIST = {
    "cpu_percent",
    "mem_used",
    "mem_total",
    "mem_percent",
    "cpu_temp",
    "disk_used",
    "disk_total",
    "disk_percent",
    "load_1",
    "load_5",
    "load_15",
    "net_bytes_sent",
    "net_bytes_recv",
    "uptime_seconds",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        REAL NOT NULL,
    cpu_percent      REAL,
    cpu_per_core     TEXT,
    mem_used         INTEGER,
    mem_total        INTEGER,
    mem_percent      REAL,
    cpu_temp         REAL,
    disk_used        INTEGER,
    disk_total       INTEGER,
    disk_percent     REAL,
    load_1           REAL,
    load_5           REAL,
    load_15          REAL,
    net_bytes_sent   INTEGER,
    net_bytes_recv   INTEGER,
    uptime_seconds   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


def insert(db_path: str, row: dict) -> None:
    columns = [
        "timestamp", "cpu_percent", "cpu_per_core", "mem_used", "mem_total",
        "mem_percent", "cpu_temp", "disk_used", "disk_total", "disk_percent",
        "load_1", "load_5", "load_15", "net_bytes_sent", "net_bytes_recv",
        "uptime_seconds",
    ]
    values = [row.get(col) for col in columns]
    placeholders = ", ".join("?" * len(columns))
    sql = f"INSERT INTO metrics ({', '.join(columns)}) VALUES ({placeholders})"
    with _connect(db_path) as conn:
        conn.execute(sql, values)


def query_latest(db_path: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    if result.get("cpu_per_core"):
        result["cpu_per_core"] = json.loads(result["cpu_per_core"])
    return result


def query_range(
    db_path: str, since_ts: float, metric: str
) -> list[tuple[float, float]]:
    if metric not in METRIC_ALLOWLIST:
        raise ValueError(f"Invalid metric: {metric!r}")
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT timestamp, {metric} FROM metrics "
            f"WHERE timestamp >= ? AND {metric} IS NOT NULL "
            f"ORDER BY timestamp ASC",
            (since_ts,),
        ).fetchall()
    return [(r[0], r[1]) for r in rows]


def prune(db_path: str, retention_days: int) -> None:
    cutoff = time.time() - retention_days * 86400
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
