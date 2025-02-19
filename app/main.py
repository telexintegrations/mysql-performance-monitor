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
import os
from os import environ

app = FastAPI()

# Configure CORS to allow specified origins (adjust as needed)
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


# Pydantic Models for integration payload
class Setting(BaseModel):
    """ Pydantic model for integration settings """
    label: str
    type: str
    required: bool
    default: str


class MonitorPayload(BaseModel):
    """ Pydantic model for the payload sent to the /tick endpoint """
    channel_id: str
    return_url: str  # This is the Telex webhook URL provided by the user.
    settings: List[Setting]


# Custom function to check MySQL server health using user-provided details.
def get_mysql_status_custom(host: str, user: str, password: str, database: str, port: int = 3306):
    """ Connects to a MySQL server and fetches its health status """
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


# Background Task: Run the MySQL health check and send results to the user's provided Telex webhook.
async def monitor_task(payload: MonitorPayload):
    """ Background task to monitor MySQL server health and send results to Telex """
    # Extract MySQL connection details from the payload's settings.
    settings_dict = {s.label: s.default for s in payload.settings}
    mysql_host = settings_dict.get("MySQL Host")
    mysql_user = settings_dict.get("MySQL User")
    mysql_password = settings_dict.get("MySQL Password")
    mysql_database = settings_dict.get("MySQL Database")
    
    # Run the synchronous MySQL check in a background thread.
    loop = asyncio.get_running_loop()
    status = await loop.run_in_executor(None, get_mysql_status_custom, mysql_host, mysql_user, mysql_password, mysql_database)
    
    # Format the health check results as a message.
    message = (
        f"MySQL Server Health Status:\n"
        f"Version: {status.get('version', 'N/A')}\n"
        f"Database Name: {status.get('dbname', 'N/A')}\n"
        f"Uptime: {status.get('uptime', 'N/A')} seconds\n"
        f"Slow Queries: {status.get('slow_queries', 'N/A')}\n"
        f"Threads Connected: {status.get('threads_connected', 'N/A')}\n"
        f"Total Connections: {status.get('connections', 'N/A')}\n"
        f"Current Open Connections: {status.get('open_conn', 'N/A')}\n"
        f"Query Cache Hits: {status.get('qcache_hits', 'N/A')}\n"
    )
    
    telex_payload = {
        "event_name": "MySQL Server Health Check",
        "message": message,
        "status": status["status"],
        "username": "MySQL Monitor"
    }
    
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(payload.return_url, json=telex_payload, headers=headers)
        print(f"Telex Response: {response.status_code}, {response.text}")
    return status


# /tick Endpoint: Triggers the MySQL health check in a background task.
# It also synchronously returns the MySQL status in JSON and a message to "Check your Telex channel".
@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    """ Endpoint to trigger the MySQL health check and send results to Telex """
    try:
        if request.method == "POST":
            payload_json = await request.json()
            monitor_payload = MonitorPayload.parse_obj(payload_json)
        else:
            # Provide a default payload with empty MySQL details if none are provided.
            monitor_payload = MonitorPayload(
                channel_id="mysql-performance-monitor",
                return_url="",  # In production, the user must supply this via integration settings.
                settings=[
                    Setting(label="MySQL Host", type="text", required=True, default=""),
                    Setting(label="MySQL User", type="text", required=True, default=""),
                    Setting(label="MySQL Password", type="text", required=True, default=""),
                    Setting(label="MySQL Database", type="text", required=True, default=""),
                    Setting(label="interval", type="text", required=True, default="*/5 * * * *")
                ]
            )
            # If no webhook URL was provided, raise an error.
            if not monitor_payload.return_url:
                raise HTTPException(status_code=400, detail="No Telex webhook URL provided in payload.")
    
        # Schedule the background task to send the Telex message using the user's provided webhook URL.
        background_tasks.add_task(monitor_task, monitor_payload)
    
        # Also, synchronously get the MySQL status for immediate JSON response.
        loop = asyncio.get_running_loop()
        mysql_status = await loop.run_in_executor(
            None,
            get_mysql_status_custom,
            monitor_payload.settings[0].default,  # MySQL Host
            monitor_payload.settings[1].default,  # MySQL User
            monitor_payload.settings[2].default,  # MySQL Password
            monitor_payload.settings[3].default   # MySQL Database
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
    """ Endpoint to return the integration configuration for Telex """
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
    """ Run the FastAPI application """
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
