# PiStat

Lightweight system monitoring dashboard for Raspberry Pi. Runs as a single Python process — no Docker, no databases to manage.

## Quick Start

**Prerequisite:** Python 3.11+

```bash
pip install -r requirements.txt
python3 main.py
# Open http://<pi-ip>:8889
```

> **Note:** Temperature reading requires `vcgencmd` (available on Raspberry Pi OS). On other Linux systems, the fallback reads from `/sys/class/thermal/`.

## Configuration

Edit `config.toml` before starting:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `[collection]` | `interval_seconds` | `10` | Seconds between metric samples |
| `[collection]` | `retention_days` | `7` | Days of history to keep |
| `[server]` | `host` | `"0.0.0.0"` | Bind address |
| `[server]` | `port` | `8889` | HTTP port |
| `[metrics]` | `network_interface` | `"eth0"` | Network interface to monitor |
| `[metrics]` | `disk_path` | `"/"` | Disk partition to monitor |
| `[database]` | `path` | `"pistat.db"` | SQLite file path |

## API Reference

### `GET /`
Serves the dashboard UI (`static/index.html`).

---

### `GET /api/current`
Latest snapshot of all metrics. Returns `204 No Content` if no data has been collected yet.

**Response** `200 OK`:
```json
{
  "id": 1,
  "timestamp": 1708747200.0,
  "cpu_percent": 12.5,
  "cpu_per_core": [10.0, 15.0, 8.0, 16.0],
  "mem_used": 512000000,
  "mem_total": 4000000000,
  "mem_percent": 12.8,
  "cpu_temp": 52.3,
  "disk_used": 10000000000,
  "disk_total": 32000000000,
  "disk_percent": 31.2,
  "load_1": 0.45,
  "load_5": 0.38,
  "load_15": 0.32,
  "net_bytes_sent": 1234567,
  "net_bytes_recv": 7654321,
  "uptime_seconds": 86400
}
```

---

### `GET /api/history?metric=<name>&hours=<n>`
Time-series data for a single metric. `hours` is clamped to a maximum of 168 (7 days). Defaults to the last 1 hour.

**Parameters:**
- `metric` — metric name from the [allowlist](#metrics-reference) (default: `cpu_percent`)
- `hours` — how many hours of history to return (default: `1`, max: `168`)

**Response** `200 OK`:
```json
[
  {"ts": 1708747200.0, "value": 12.5},
  {"ts": 1708747210.0, "value": 14.2}
]
```

**Response** `400 Bad Request` — metric name not in allowlist:
```json
{"error": "Invalid metric: 'bad_metric'"}
```

---

### `GET /api/export?hours=<n>`
Download all stored data as a CSV file. `hours` is clamped to 168.

**Parameters:**
- `hours` — how many hours of data to export (default: `24`, max: `168`)

**Response** `200 OK` — `Content-Type: text/csv`, `Content-Disposition: attachment; filename=pistat_export.csv`

```
id,timestamp,cpu_percent,cpu_per_core,...
1,1708747200.0,12.5,"[10.0, 15.0]",...
```

---

### `GET /api/config`
Current configuration values as JSON.

**Response** `200 OK`:
```json
{
  "interval_seconds": 10,
  "retention_days": 7,
  "network_interface": "eth0",
  "disk_path": "/",
  "host": "0.0.0.0",
  "port": 8889
}
```

## Metrics Reference

| Metric | Unit | Source |
|--------|------|--------|
| `cpu_percent` | % | psutil |
| `cpu_per_core` | JSON array of % | psutil |
| `mem_used` | bytes | psutil |
| `mem_total` | bytes | psutil |
| `mem_percent` | % | psutil |
| `cpu_temp` | °C | vcgencmd / sysfs |
| `disk_used` | bytes | psutil |
| `disk_total` | bytes | psutil |
| `disk_percent` | % | psutil |
| `load_1` | — | psutil |
| `load_5` | — | psutil |
| `load_15` | — | psutil |
| `net_bytes_sent` | bytes cumulative | psutil |
| `net_bytes_recv` | bytes cumulative | psutil |
| `uptime_seconds` | seconds | psutil |

> **Note:** `cpu_per_core` is stored and returned by `/api/current` but is not available via `/api/history` (it is an array, not a scalar value).

## Running as a Service

```bash
# Copy the unit file (edit WorkingDirectory and ExecStart paths if installed elsewhere)
sudo cp pistat.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable pistat
sudo systemctl start pistat
sudo systemctl status pistat
```

## Architecture

PiStat is a single Python process: a Flask HTTP server runs alongside a background daemon thread that collects metrics on a configurable interval (default 10 seconds) and writes them to SQLite. The database uses an indexed timestamp column and a prune job that removes rows older than the configured retention window. Metrics are collected via psutil, with temperature reading from `vcgencmd` and a sysfs fallback. Each metric collector is wrapped in try/except so a single sensor failure never drops an entire sample. The frontend polls `/api/current` every 5 seconds for live stats and `/api/history` every 60 seconds to refresh charts — no WebSockets required.

## Development

### Project Structure

| File | Role |
|------|------|
| `main.py` | Entry point: wires everything together |
| `pistat/config.py` | TOML config loader using dataclasses |
| `pistat/db.py` | SQLite schema, inserts, queries, pruning, metric allowlist |
| `pistat/collector.py` | psutil metrics; background daemon thread; temperature via vcgencmd or sysfs fallback |
| `pistat/server.py` | Flask app factory with all routes |
| `static/index.html` | Single-page UI |
| `static/app.js` | Polling logic, Chart.js charts, color thresholds |
| `static/style.css` | Dark theme, responsive grid |
| `config.toml` | Runtime config (interval, retention, host/port, interface, disk path) |
| `pistat.service` | systemd unit file |

### Adding a New Metric

1. Add a collector function in `pistat/collector.py` wrapped in try/except, and call it from `collect_all()`.
2. Add a column to the `SCHEMA` string in `pistat/db.py`, and add the metric name to `METRIC_ALLOWLIST` if it is a scalar value suitable for time-series queries.
3. Update `static/app.js` and `static/index.html` to display the new metric card if desired.

### Running Tests

```bash
pip install pytest
pytest tests/ -v

# With coverage
pip install pytest-cov
pytest tests/ --cov=pistat --cov-report=term-missing
```
