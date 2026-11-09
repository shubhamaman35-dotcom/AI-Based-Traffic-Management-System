import pytest
from starlette.testclient import TestClient
from server.app import app


client = TestClient(app)


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI-STMS CORE" in response.text
    assert "4-Way Simulator" in response.text


def test_api_set_mode():
    response = client.post("/api/control/mode", data={"mode": "FIXED_TIME"})
    assert response.status_code == 200
    assert response.json()["mode"] == "FIXED_TIME"

    # Reset back to ADAPTIVE
    response = client.post("/api/control/mode", data={"mode": "ADAPTIVE"})
    assert response.status_code == 200
    assert response.json()["mode"] == "ADAPTIVE"


def test_api_set_scenario():
    response = client.post("/api/control/scenario", data={"scenario": "RUSH_HOUR"})
    assert response.status_code == 200
    assert response.json()["scenario"] == "RUSH_HOUR"


def test_api_trigger_emergency():
    response = client.post("/api/control/emergency", data={"lane": "north"})
    assert response.status_code == 200
    assert response.json()["status"] == "dispatched"
    assert response.json()["lane"] == "north"


def test_api_toggle_blockage():
    response = client.post("/api/control/toggle-blockage", data={"lane": "south"})
    assert response.status_code == 200
    assert "is_blocked" in response.json()


def test_api_export_metrics():
    # JSON export
    res_json = client.get("/api/metrics/export?format=json")
    assert res_json.status_code == 200
    assert "metrics" in res_json.json()

    # CSV export
    res_csv = client.get("/api/metrics/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Metric,Value" in res_csv.text
