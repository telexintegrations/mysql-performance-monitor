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
import requests
import httpx
import pymysql
from dotenv import load_dotenv
import os

# Load environment variables (if any non-sensitive configs are needed)
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


# Pydantic Models for integration payload
class Setting(BaseModel):
    """
    Represents a configuration setting for the integration.

    Attributes:
        label (str): The unique label of the setting.
        type (str): The data type of the setting (e.g., "text", "number").
        required (bool): Indicates if this setting is mandatory.
        default (str): The default value for this setting.
    """
    label: str
    type: str
    required: bool
    default: str


class MonitorPayload(BaseModel):
    """
    Represents the payload for triggering the MySQL monitoring integration.

    Attributes:
        channel_id (str): The unique channel identifier.
        return_url (str): The user-provided Telex webhook URL where the health status is sent.
        settings (List[Setting]): A list of settings containing MySQL and webhook configuration.
    """
    channel_id: str
    return_url: str
    settings: List[Setting]


# Global variable to hold the current payload for MySQL settings.
current_payload = None


def get_mysql_status_custom(host: str, user: str, password: str, database: str, port: int = 3306):
    """
    Connects to the MySQL server using the provided parameters and fetches various health metrics.

    Args:
        host (str): MySQL server host.
        user (str): MySQL username.
        password (str): MySQL password.
        database (str): Database to connect to.
        port (int, optional): Port number for MySQL. Defaults to 3306.

    Returns:
        dict: A dictionary containing MySQL server health status and metrics, or an error message.
    """
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
        cursor.execute(
            "SELECT COUNT(*) AS open_conn FROM information_schema.processlist;")
        open_conn = cursor.fetchone()

        # Query Cache Hits
        cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
        qcache_hits = cursor.fetchone()

        # Available Tables in the database
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        table_names = [list(row.values())[0] for row in tables]

        cursor.close()
        connection.close()

        return {
            "version": version["version"] if version else "Unknown",
            "dbname": dbname["dbname"] if dbname else "Unknown",
            "tables": table_names,
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


def send_to_telex(webhook_url: str):
    """
    Sends the MySQL server health status to the Telex channel using the provided webhook URL.

    Args:
        webhook_url (str): The Telex webhook URL supplied by the user.

    Returns:
        dict: The response from the Telex webhook as a JSON object.
    """
    mysql_status = get_mysql_status_custom(
        host=next(
            s.default for s in current_payload.settings if s.label == "MySQL Host"),
        user=next(
            s.default for s in current_payload.settings if s.label == "MySQL User"),
        password=next(
            s.default for s in current_payload.settings if s.label == "MySQL Password"),
        database=next(
            s.default for s in current_payload.settings if s.label == "MySQL Database")
    )
    payload = {
        "event_name": "MySQL Server Health Check",
        "message": (
            f"MySQL Server Health Status:\n"
            f"Version: {mysql_status.get('version', 'N/A')}\n"
            f"Database Name: {mysql_status.get('dbname', 'N/A')}\n"
            f"Available Tables: {', '.join(mysql_status.get('tables', []))}\n"
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


async def monitor_task(payload: MonitorPayload):
    """
    Background task to perform the MySQL health check and send the results to the Telex channel.

    Args:
        payload (MonitorPayload): The integration payload containing MySQL and webhook configuration.
    """
    global current_payload
    # Store the current payload for use in send_to_telex().
    current_payload = payload
    send_to_telex(payload.return_url)


@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    The /tick endpoint triggers the MySQL health check.
    It runs the check in a background task and also returns the MySQL status immediately in JSON.

    Returns:
        JSONResponse: Contains the MySQL status and a message to check the Telex channel.
    """
    try:
        if request.method == "POST":
            payload_json = await request.json()
            monitor_payload = MonitorPayload.parse_obj(payload_json)
        else:
            # For GET requests, construct a default payload (user must provide valid settings)
            monitor_payload = MonitorPayload(
                channel_id="mysql-performance-monitor",
                return_url="",  # No default, user must supply their Telex webhook URL
                settings=[
                    Setting(label="MySQL Host", type="text",
                            required=True, default=""),
                    Setting(label="MySQL User", type="text",
                            required=True, default=""),
                    Setting(label="MySQL Password", type="text",
                            required=True, default=""),
                    Setting(label="MySQL Database", type="text",
                            required=True, default=""),
                    Setting(label="WebHook URL Configuration",
                            type="text", required=True, default=""),
                    Setting(label="interval", type="text",
                            required=True, default="*/5 * * * *")
                ]
            )
            # If no webhook URL provided, raise an error.
            if not monitor_payload.return_url or not any(s.default for s in monitor_payload.settings if s.label == "WebHook URL Configuration"):
                raise HTTPException(
                    status_code=400, detail="No Telex webhook URL provided in payload.")

        # Schedule the background task to send the Telex message using the user's provided webhook URL.
        background_tasks.add_task(monitor_task, monitor_payload)

        # Also, synchronously get the MySQL status using the user-supplied settings.
        settings_dict = {s.label: s.default for s in monitor_payload.settings}
        mysql_host = settings_dict.get("MySQL Host")
        mysql_user = settings_dict.get("MySQL User")
        mysql_password = settings_dict.get("MySQL Password")
        mysql_database = settings_dict.get("MySQL Database")

        loop = asyncio.get_running_loop()
        mysql_status = await loop.run_in_executor(
            None,
            get_mysql_status_custom,
            mysql_host, mysql_user, mysql_password, mysql_database
        )

        return JSONResponse(status_code=202, content={
            "mysql_status": mysql_status,
            "message": "Check your Telex channel"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/integration.json")
def get_integration_config(request: Request):
    """
    Returns the integration configuration for Telex.

    The configuration includes metadata, key features, and the required settings for
    the MySQL Performance Monitor integration.

    Returns:
        JSONResponse: The integration configuration in JSON format.
    """
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
                        "default": "*/20 * * * *"
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
