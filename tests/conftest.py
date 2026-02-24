import pytest
from pistat.config import Config, CollectionConfig, ServerConfig, MetricsConfig, DatabaseConfig
from pistat.db import init_db
from pistat import server as server_module


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


@pytest.fixture
def mock_config(tmp_path):
    return Config(
        collection=CollectionConfig(interval_seconds=10, retention_days=7),
        server=ServerConfig(host="127.0.0.1", port=8080),
        metrics=MetricsConfig(network_interface="eth0", disk_path="/"),
        database=DatabaseConfig(path=str(tmp_path / "test.db")),
    )


@pytest.fixture
def client(mock_config, tmp_db, monkeypatch):
    mock_config.database.path = tmp_db
    # Prevent background collector thread from starting during tests
    # create_app() unconditionally starts a daemon thread at server.py:27
    monkeypatch.setattr(
        "pistat.server.threading.Thread",
        lambda **kwargs: type("T", (), {"start": lambda self: None})(),
    )
    app = server_module.create_app(mock_config)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
