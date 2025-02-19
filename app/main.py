"""
The main file for the FastAPI application.
This module logs the MySQL server health status to a Telex channel.
"""

import asyncio
import json
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import pymysql
from dotenv import load_dotenv
import os
from os import getenv, environ

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS to allow specified origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://staging.telextest.im",
        "http://telextest.im",
        "https://staging.telex.im",
        "https://telex.im",
        "https://mysql-performance-monitor.onrender.com",
        "https://learnopolia.tech"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Pydantic Models for integration payload
class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str

class MonitorPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: List[Setting]

# A custom function to check MySQL server health with given parameters.
def get_mysql_status_custom(host: str, user: str, password: str, database: str, port: int = 3306):
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("\nConnected to MySQL successfully.\nFetching MySQL Server Health Status...")
        cursor = connection.cursor()

        # MySQL Version
        cursor.execute("SELECT VERSION() AS version;")
        version = cursor.fetchone()

        # Database Name
        cursor.execute("SELECT DATABASE() AS dbname;")
        dbname = cursor.fetchone()

        # Uptime
        cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
        uptime = cursor.fetchone()

        # Slow Queries
        cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
        slow_queries = cursor.fetchone()

        # Threads Connected
        cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
        threads_connected = cursor.fetchone()

        # Total Connections
        cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
        connections = cursor.fetchone()

        # Current Open Connections
        cursor.execute("SELECT COUNT(*) AS open_conn FROM information_schema.processlist;")
        open_conn = cursor.fetchone()

        # Query Cache Hits
        cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
        qcache_hits = cursor.fetchone()

        cursor.close()
        connection.close()

        return {
            "version": version["version"] if version else "Unknown",
            "dbname": dbname["dbname"] if dbname else "Unknown",
            "uptime": uptime["Value"] if uptime else "Unknown",
            "slow_queries": slow_queries["Value"] if slow_queries else "Unknown",
            "threads_connected": threads_connected["Value"] if threads_connected else "Unknown",
            "connections": connections["Value"] if connections else "Unknown",
            "open_conn": open_conn["open_conn"] if open_conn else "Unknown",
            "qcache_hits": qcache_hits["Value"] if qcache_hits else "Unknown",
            "status": "success"
        }
    except pymysql.MySQLError as err:
        return {
            "error": str(err),
            "status": "failure"
        }

# Modified send_to_telex() now accepts a webhook_url parameter.
def send_to_telex(webhook_url: str):
    """
    Sends the MySQL server health status to the Telex channel using the provided webhook URL.
    """
    mysql_status = get_mysql_status_custom(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    payload = {
        "event_name": "MySQL Server Health Check",
        "message": (
            f"MySQL Server Health Status:\n"
            f"Version: {mysql_status.get('version', 'N/A')}\n"
            f"Database Name: {mysql_status.get('dbname', 'N/A')}\n"
            f"Uptime: {mysql_status.get('uptime', 'N/A')} seconds\n"
            f"Slow Queries: {mysql_status.get('slow_queries', 'N/A')}\n"
            f"Threads Connected: {mysql_status.get('threads_connected', 'N/A')}\n"
            f"Total Connections: {mysql_status.get('connections', 'N/A')}\n"
            f"Current Open Connections: {mysql_status.get('open_conn', 'N/A')}\n"
            f"Query Cache Hits: {mysql_status.get('qcache_hits', 'N/A')}\n"
        ),
        "status": mysql_status["status"],
        "username": "MySQL Monitor"
    }
    print("Sending the following message to Telex:\n", payload.get("message"))
    response = requests.post(
        webhook_url,
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )
    print("Telex Response:", response.json())
    return response.json()

# Background Task: Run monitor_task to send the status using the user's webhook URL.
async def monitor_task(payload: MonitorPayload):
    # Use the user's webhook URL from the payload
    webhook_url = payload.return_url
    # Send to Telex using the provided webhook URL
    send_to_telex(webhook_url)

# /tick Endpoint: Triggers the MySQL health check in a background task,
# returns the MySQL status in JSON, and includes the message "Check your Telex channel".
@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    try:
        if request.method == "POST":
            payload_json = await request.json()
            monitor_payload = MonitorPayload.parse_obj(payload_json)
        else:
            monitor_payload = MonitorPayload(
                channel_id="mysql-performance-monitor",
                return_url=os.getenv("TELEX_WEBHOOK_URL", "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e"),
                settings=[
                    Setting(label="MySQL Host", type="text", required=True, default=os.getenv("MYSQL_HOST", "localhost")),
                    Setting(label="MySQL User", type="text", required=True, default=os.getenv("MYSQL_USER", "root")),
                    Setting(label="MySQL Password", type="text", required=True, default=os.getenv("MYSQL_PASSWORD", "")),
                    Setting(label="MySQL Database", type="text", required=True, default=os.getenv("MYSQL_DATABASE", "test_db")),
                    Setting(label="WebHook URL Configuration", type="text", required=True, default=os.getenv("TELEX_WEBHOOK_URL", "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e")),
                    Setting(label="interval", type="text", required=True, default="*/5 * * * *")
                ]
            )
        # Schedule the background task to send the Telex message using the user's webhook URL.
        background_tasks.add_task(monitor_task, monitor_payload)
    
        # Also, synchronously get the MySQL status for immediate JSON response.
        loop = asyncio.get_running_loop()
        mysql_status = await loop.run_in_executor(
            None,
            get_mysql_status_custom,
            os.getenv("MYSQL_HOST", "localhost"),
            os.getenv("MYSQL_USER", "root"),
            os.getenv("MYSQL_PASSWORD", ""),
            os.getenv("MYSQL_DATABASE", "test_db")
        )
    
        return JSONResponse(status_code=202, content={
            "mysql_status": mysql_status,
            "message": "Check your Telex channel"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# /integration.json Endpoint: Returns the integration configuration for Telex.
@app.get("/integration.json")
def get_integration_config(request: Request):
    try:
        base_url = str(request.base_url).rstrip("/")
        return {
            "data": {
                "date": {
                    "created_at": "2025-02-18",
                    "updated_at": "2025-02-18"
                },
                "descriptions": {
                    "app_name": "MySQL Performance Monitor",
                    "app_description": "Monitors MySQL Databases in real time",
                    "app_logo": "https://i.imgur.com/lZqvffp.png",
                    "app_url": base_url,
                    "background_color": "#fff"
                },
                "is_active": "true",
                "integration_category": "Monitoring & Logging",
                "integration_type": "interval",
                "key_features": [
                    "Monitors a remote MySQL server",
                    "Logs MySQL Server health status to the Telex channel"
                ],
                "author": "Dohou Daniel Favour",
                "settings": [
                    {
                        "label": "MySQL Host",
                        "type": "text",
                        "required": "true",
                        "default": ""
                    },
                    {
                        "label": "MySQL User",
                        "type": "text",
                        "required": "true",
                        "default": ""
                    },
                    {
                        "label": "MySQL Password",
                        "type": "text",
                        "required": "true",
                        "default": ""
                    },
                    {
                        "label": "MySQL Database",
                        "type": "text",
                        "required": "true",
                        "default": ""
                    },
                    {
                        "label": "WebHook URL Configuration",
                        "type": "text",
                        "required": "true",
                        "default": ""
                    },
                    {
                        "label": "interval",
                        "type": "text",
                        "required": "true",
                        "default": "*/5 * * * *"
                    }
                ],
                "target_url": f"{base_url}/tick",
                "tick_url": f"{base_url}/tick"
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Failed to generate integration JSON"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
