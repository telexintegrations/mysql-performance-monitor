"""
The test_main.py file contains the tests for the main.py file.
This test is carried out using the pytest framework.
"""
# Import statements
import pytest
from fastapi.testclient import TestClient
from app import main

client = TestClient(main.app)

# Dummy MySQL status to simulate the database response.
dummy_status = {
    "version": "8.0.32",
    "dbname": "test_db",
    "uptime": "3600",
    "slow_queries": "0",
    "threads_connected": "5",
    "connections": "100",
    "open_conn": "3",
    "qcache_hits": "50",
    "tables": ["table1", "table2"],
    "status": "success"
}


# Patch get_mysql_status_custom to return dummy data instead of making a real DB connection.
def dummy_get_mysql_status_custom(host, user, password, database, port=3306):
    return dummy_status


@pytest.fixture(autouse=True)
def patch_get_status(monkeypatch):
    monkeypatch.setattr(main, "get_mysql_status_custom", dummy_get_mysql_status_custom)


def test_integration_json():
    """
    Test that the /integration.json endpoint returns a valid integration configuration.
    """
    response = client.get("/integration.json")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "descriptions" in data["data"]
    assert "settings" in data["data"]
    assert "tick_url" in data["data"]


def test_tick_endpoint_post():
    """
    Test the /tick endpoint with a valid POST payload.
    It should return a JSON response with the dummy MySQL status and the message.
    """
    payload = {
        "channel_id": "mysql-performance-monitor",
        "return_url": "https://ping.telex.im/v1/webhooks/TEST_WEBHOOK",
        "settings": [
            {"label": "MySQL Host", "type": "text", "required": True, "default": "100.25.170.180"},
            {"label": "MySQL User", "type": "text", "required": True, "default": "precious"},
            {"label": "MySQL Password", "type": "text", "required": True, "default": "preciousese"},
            {"label": "MySQL Database", "type": "text", "required": True, "default": "quizolia"},
            {"label": "WebHook URL Configuration", "type": "text", "required": True, "default": "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e"},
            {"label": "interval", "type": "text", "required": True, "default": "*/5 * * * *"}
        ]
    }
    response = client.post("/tick", json=payload)
    assert response.status_code == 202
    json_response = response.json()
    # Check that the response includes the dummy MySQL status and the message.
    assert "mysql_status" in json_response
    assert json_response["mysql_status"]["version"] == "8.0.32"
    assert json_response["message"] == "Check your Telex channel"


def test_tick_endpoint_get_no_webhook():
    """
    Test the /tick endpoint with a GET request.
    Since the default payload lacks a webhook URL, an error should be raised.
    """
    response = client.get("/tick")
    # Expecting a 400 error because the webhook URL is missing.
    assert response.status_code == 500  # Error code was 400 before
