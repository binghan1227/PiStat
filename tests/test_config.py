import pytest
from pistat.config import load_config, Config

VALID_TOML = """\
[collection]
interval_seconds = 10
retention_days = 7

[server]
host = "0.0.0.0"
port = 8889

[metrics]
network_interface = "eth0"
disk_path = "/"

[database]
path = "pistat.db"
"""


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(VALID_TOML)
    return str(p)


def test_load_valid_config(config_file):
    config = load_config(config_file)
    assert isinstance(config, Config)
    assert config.collection.interval_seconds == 10
    assert config.collection.retention_days == 7
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 8889
    assert config.metrics.network_interface == "eth0"
    assert config.metrics.disk_path == "/"
    assert config.database.path == "pistat.db"


def test_load_defaults_present(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("""\
[collection]
interval_seconds = 30
retention_days = 14

[server]
host = "127.0.0.1"
port = 9090

[metrics]
network_interface = "wlan0"
disk_path = "/home"

[database]
path = "/tmp/pistat.db"
""")
    config = load_config(str(p))
    assert config.collection.interval_seconds == 30
    assert config.collection.retention_days == 14
    assert config.server.port == 9090
    assert config.metrics.network_interface == "wlan0"


def test_load_invalid_toml_raises(tmp_path):
    p = tmp_path / "config.toml"
    p.write_bytes(b"not valid toml [[[")
    with pytest.raises(Exception):
        load_config(str(p))


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nonexistent.toml"))


def test_collection_config_types(config_file):
    config = load_config(config_file)
    assert isinstance(config.collection.interval_seconds, int)
    assert isinstance(config.collection.retention_days, int)


def test_server_config_port_type(config_file):
    config = load_config(config_file)
    assert isinstance(config.server.port, int)


def test_metrics_config_values(config_file):
    config = load_config(config_file)
    assert isinstance(config.metrics.network_interface, str)
    assert isinstance(config.metrics.disk_path, str)


def test_database_config_path(config_file):
    config = load_config(config_file)
    assert isinstance(config.database.path, str)
