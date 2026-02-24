import json
import subprocess
import time

import psutil


def _cpu() -> dict:
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "cpu_per_core": json.dumps(psutil.cpu_percent(percpu=True)),
        }
    except Exception:
        return {}


def _memory() -> dict:
    try:
        mem = psutil.virtual_memory()
        return {
            "mem_used": mem.used,
            "mem_total": mem.total,
            "mem_percent": mem.percent,
        }
    except Exception:
        return {}


def _temperature() -> dict:
    # Try vcgencmd first (more accurate on Pi)
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_temp"], timeout=2, text=True
        )
        # output: "temp=58.7'C\n"
        temp = float(out.strip().split("=")[1].rstrip("'C"))
        return {"cpu_temp": temp}
    except Exception:
        pass

    # Fall back to thermal zone sysfs
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return {"cpu_temp": int(f.read().strip()) / 1000.0}
    except Exception:
        return {"cpu_temp": None}


def _disk(path: str) -> dict:
    try:
        usage = psutil.disk_usage(path)
        return {
            "disk_used": usage.used,
            "disk_total": usage.total,
            "disk_percent": usage.percent,
        }
    except Exception:
        return {}


def _load() -> dict:
    try:
        load1, load5, load15 = psutil.getloadavg()
        return {"load_1": load1, "load_5": load5, "load_15": load15}
    except Exception:
        return {}


def _network(iface: str) -> dict:
    try:
        counters = psutil.net_io_counters(pernic=True)
        if iface not in counters:
            # Fall back to aggregate
            agg = psutil.net_io_counters()
            return {
                "net_bytes_sent": agg.bytes_sent,
                "net_bytes_recv": agg.bytes_recv,
            }
        nic = counters[iface]
        return {
            "net_bytes_sent": nic.bytes_sent,
            "net_bytes_recv": nic.bytes_recv,
        }
    except Exception:
        return {}


def _uptime() -> dict:
    try:
        return {"uptime_seconds": int(time.time() - psutil.boot_time())}
    except Exception:
        return {}


def collect_all(config) -> dict:
    row: dict = {"timestamp": time.time()}
    row.update(_cpu())
    row.update(_memory())
    row.update(_temperature())
    row.update(_disk(config.metrics.disk_path))
    row.update(_load())
    row.update(_network(config.metrics.network_interface))
    row.update(_uptime())
    return row
