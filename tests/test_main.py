from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_integration_json():
    response = client.get("/integration.json")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "descriptions" in data["data"]


def test_tick_endpoint():
    payload = {
        "channel_id": "test-channel",
        "return_url": "http://example.com/return",
        "settings": [
            {"label": "mysql_host", "type": "text", "required": True, "default": "localhost"},
            {"label": "mysql_user", "type": "text", "required": True, "default": "root"},
            {"label": "mysql_password", "type": "text", "required": True, "default": ""},
            {"label": "mysql_database", "type": "text", "required": True, "default": "testdb"},
            {"label": "last_log_id", "type": "text", "required": False, "default": "0"},
            {"label": "interval", "type": "text", "required": True, "default": "* * * * *"}
        ]
    }
    response = client.post("/tick", json=payload)
    assert response.status_code == 202
    json_data = response.json()
    assert json_data.get("status") == "accepted"
    assert json_data.get("message") == "Monitoring started"
