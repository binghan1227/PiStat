import csv
import io
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

from .collector import collect_all
from .db import METRIC_ALLOWLIST, insert, prune, query_latest, query_range


def _collector_loop(config) -> None:
    while True:
        try:
            row = collect_all(config)
            insert(config.database.path, row)
            prune(config.database.path, config.collection.retention_days)
        except Exception as exc:
            print(f"[collector] error: {exc}")
        time.sleep(config.collection.interval_seconds)


def create_app(config) -> Flask:
    app = Flask(__name__, static_folder="../static", static_url_path="")

    # Start background collector thread
    t = threading.Thread(target=_collector_loop, args=(config,), daemon=True)
    t.start()

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/current")
    def api_current():
        row = query_latest(config.database.path)
        if row is None:
            return jsonify({}), 204
        return jsonify(row)

    @app.route("/api/history")
    def api_history():
        metric = request.args.get("metric", "cpu_percent")
        if metric not in METRIC_ALLOWLIST:
            return jsonify({"error": f"Invalid metric: {metric!r}"}), 400

        try:
            hours = min(float(request.args.get("hours", 1)), 168)
        except ValueError:
            hours = 1

        since_ts = time.time() - hours * 3600
        rows = query_range(config.database.path, since_ts, metric)
        return jsonify([{"ts": ts, "value": val} for ts, val in rows])

    @app.route("/api/export")
    def api_export():
        try:
            hours = min(float(request.args.get("hours", 24)), 168)
        except ValueError:
            hours = 24

        since_ts = time.time() - hours * 3600
        # Collect all metrics for CSV export
        metrics = list(METRIC_ALLOWLIST)
        metrics.sort()

        # Build combined rows by querying each metric
        from .db import _connect
        import sqlite3
        with _connect(config.database.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM metrics WHERE timestamp >= ? ORDER BY timestamp ASC",
                (since_ts,),
            ).fetchall()

        output = io.StringIO()
        if rows:
            fieldnames = list(rows[0].keys())
        else:
            fieldnames = ["timestamp"] + sorted(METRIC_ALLOWLIST)

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

        csv_bytes = output.getvalue().encode()
        return app.response_class(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=pistat_export.csv"},
        )

    @app.route("/api/config")
    def api_config():
        return jsonify({
            "interval_seconds": config.collection.interval_seconds,
            "retention_days": config.collection.retention_days,
            "network_interface": config.metrics.network_interface,
            "disk_path": config.metrics.disk_path,
            "host": config.server.host,
            "port": config.server.port,
        })

    return app
