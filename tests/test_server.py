import time

import pytest

from pistat.db import insert


def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_current_empty_returns_204(client):
    response = client.get("/api/current")
    assert response.status_code == 204


def test_current_with_data_returns_200(client, tmp_db):
    insert(tmp_db, {"timestamp": time.time(), "cpu_percent": 55.0, "mem_percent": 40.0})
    response = client.get("/api/current")
    assert response.status_code == 200


def test_current_response_has_expected_keys(client, tmp_db):
    insert(tmp_db, {
        "timestamp": time.time(),
        "cpu_percent": 55.0,
        "mem_percent": 40.0,
        "disk_percent": 30.0,
    })
    response = client.get("/api/current")
    data = response.get_json()
    assert "cpu_percent" in data
    assert "mem_percent" in data
    assert "timestamp" in data


def test_history_invalid_metric_returns_400(client):
    response = client.get("/api/history?metric=not_a_real_metric")
    assert response.status_code == 400


def test_history_valid_metric_returns_200(client):
    response = client.get("/api/history?metric=cpu_percent")
    assert response.status_code == 200


def test_history_clamps_hours_to_168(client):
    response = client.get("/api/history?metric=cpu_percent&hours=99999")
    assert response.status_code == 200


def test_history_response_shape(client, tmp_db):
    insert(tmp_db, {"timestamp": time.time(), "cpu_percent": 55.0})
    response = client.get("/api/history?metric=cpu_percent")
    data = response.get_json()
    assert len(data) > 0
    assert "ts" in data[0]
    assert "value" in data[0]


def test_export_returns_csv(client):
    response = client.get("/api/export")
    assert "text/csv" in response.content_type


def test_export_has_correct_headers(client, tmp_db):
    insert(tmp_db, {"timestamp": time.time(), "cpu_percent": 55.0})
    response = client.get("/api/export")
    csv_text = response.data.decode("utf-8")
    header_line = csv_text.splitlines()[0]
    assert "timestamp" in header_line


def test_export_clamps_hours(client):
    response = client.get("/api/export?hours=99999")
    assert response.status_code == 200


def test_config_endpoint_returns_200(client):
    response = client.get("/api/config")
    assert response.status_code == 200


def test_config_has_expected_keys(client):
    data = client.get("/api/config").get_json()
    for key in ["interval_seconds", "retention_days", "network_interface", "disk_path", "host", "port"]:
        assert key in data


def test_config_values_match_mock_config(client):
    data = client.get("/api/config").get_json()
    assert data["network_interface"] == "eth0"
    assert data["port"] == 8080
    assert data["host"] == "127.0.0.1"
    assert data["interval_seconds"] == 10
    assert data["retention_days"] == 7
