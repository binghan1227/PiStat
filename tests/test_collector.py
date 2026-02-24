import pytest
from unittest.mock import patch, Mock, mock_open

from pistat.collector import (
    _cpu,
    _disk,
    _load,
    _memory,
    _network,
    _temperature,
    _uptime,
    collect_all,
)


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

def test_cpu_returns_expected_keys():
    with patch("pistat.collector.psutil.cpu_percent", side_effect=[55.0, [10.0, 20.0]]):
        result = _cpu()
    assert "cpu_percent" in result
    assert "cpu_per_core" in result
    assert result["cpu_percent"] == pytest.approx(55.0)


def test_cpu_exception_returns_empty():
    with patch("pistat.collector.psutil.cpu_percent", side_effect=RuntimeError("fail")):
        result = _cpu()
    assert result == {}


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def test_memory_returns_expected_keys():
    mock_mem = Mock(used=1_000_000, total=4_000_000, percent=25.0)
    with patch("pistat.collector.psutil.virtual_memory", return_value=mock_mem):
        result = _memory()
    assert result == {"mem_used": 1_000_000, "mem_total": 4_000_000, "mem_percent": 25.0}


def test_memory_exception_returns_empty():
    with patch("pistat.collector.psutil.virtual_memory", side_effect=RuntimeError("fail")):
        result = _memory()
    assert result == {}


# ---------------------------------------------------------------------------
# Temperature
# ---------------------------------------------------------------------------

def test_temperature_vcgencmd_success():
    with patch("pistat.collector.subprocess.check_output", return_value="temp=42.0'C\n"):
        result = _temperature()
    assert result["cpu_temp"] == pytest.approx(42.0)


def test_temperature_vcgencmd_failure_falls_back_to_sysfs():
    with patch("pistat.collector.subprocess.check_output", side_effect=FileNotFoundError), \
         patch("builtins.open", mock_open(read_data="42000")):
        result = _temperature()
    assert result["cpu_temp"] == pytest.approx(42.0)


def test_temperature_both_fail_returns_none():
    with patch("pistat.collector.subprocess.check_output", side_effect=FileNotFoundError), \
         patch("builtins.open", side_effect=OSError):
        result = _temperature()
    assert result.get("cpu_temp") is None


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

def test_disk_returns_expected_keys():
    mock_usage = Mock(used=10_000_000, total=32_000_000, percent=31.2)
    with patch("pistat.collector.psutil.disk_usage", return_value=mock_usage):
        result = _disk("/")
    assert result == {
        "disk_used": 10_000_000,
        "disk_total": 32_000_000,
        "disk_percent": 31.2,
    }


def test_disk_exception_returns_empty():
    with patch("pistat.collector.psutil.disk_usage", side_effect=PermissionError):
        result = _disk("/")
    assert result == {}


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def test_load_returns_three_values():
    with patch("pistat.collector.psutil.getloadavg", return_value=(0.5, 0.6, 0.7)):
        result = _load()
    assert result == {"load_1": 0.5, "load_5": 0.6, "load_15": 0.7}


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def test_network_uses_configured_interface():
    nic = Mock(bytes_sent=1000, bytes_recv=2000)
    with patch("pistat.collector.psutil.net_io_counters", return_value={"eth0": nic}):
        result = _network("eth0")
    assert result == {"net_bytes_sent": 1000, "net_bytes_recv": 2000}


def test_network_falls_back_to_aggregate():
    agg = Mock(bytes_sent=5000, bytes_recv=6000)
    # First call (pernic=True) returns empty dict — interface not found
    # Second call (no args) returns aggregate counters
    with patch("pistat.collector.psutil.net_io_counters", side_effect=[{}, agg]):
        result = _network("eth0")
    assert result == {"net_bytes_sent": 5000, "net_bytes_recv": 6000}


def test_network_exception_returns_empty():
    with patch("pistat.collector.psutil.net_io_counters", side_effect=RuntimeError):
        result = _network("eth0")
    assert result == {}


# ---------------------------------------------------------------------------
# collect_all
# ---------------------------------------------------------------------------

def _mock_config():
    cfg = Mock()
    cfg.metrics.disk_path = "/"
    cfg.metrics.network_interface = "eth0"
    return cfg


def test_collect_all_has_timestamp():
    with patch("pistat.collector._cpu", return_value={}), \
         patch("pistat.collector._memory", return_value={}), \
         patch("pistat.collector._temperature", return_value={}), \
         patch("pistat.collector._disk", return_value={}), \
         patch("pistat.collector._load", return_value={}), \
         patch("pistat.collector._network", return_value={}), \
         patch("pistat.collector._uptime", return_value={}):
        result = collect_all(_mock_config())
    assert "timestamp" in result


def test_collect_all_merges_all_collectors():
    with patch("pistat.collector._cpu", return_value={"cpu_percent": 50.0}), \
         patch("pistat.collector._memory", return_value={"mem_percent": 60.0}), \
         patch("pistat.collector._temperature", return_value={"cpu_temp": 42.0}), \
         patch("pistat.collector._disk", return_value={"disk_percent": 70.0}), \
         patch("pistat.collector._load", return_value={"load_1": 0.5}), \
         patch("pistat.collector._network", return_value={"net_bytes_sent": 1000}), \
         patch("pistat.collector._uptime", return_value={"uptime_seconds": 3600}):
        result = collect_all(_mock_config())
    assert result["cpu_percent"] == 50.0
    assert result["mem_percent"] == 60.0
    assert result["disk_percent"] == 70.0
    assert result["cpu_temp"] == 42.0
    assert result["uptime_seconds"] == 3600
