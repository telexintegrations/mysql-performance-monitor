"""
The main file for the FastAPI application.
This module logs the MySQL server health status to a Telex channel.
"""

import pymysql
import requests
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from starlette.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from os import getenv, environ

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS to allow specific origins (adjust the list as needed)
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

# MySQL Connection Credentials
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "test_db")

# Telex Webhook URL
TELEX_WEBHOOK_URL = os.getenv("TELEX_WEBHOOK_URL", "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e")


def get_mysql_status():
    """
    Connects to the MySQL server and runs several health-check commands.
    Returns a dictionary containing the MySQL server health status.
    """
    try:
        # Establish connection using PyMySQL
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
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


def send_to_telex():
    """
    Sends the MySQL server health status to the Telex channel using a webhook.
    """
    mysql_status = get_mysql_status()
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
        "username": "server-monitor"
    }

    print("Sending the following message to Telex:\n", payload.get("message"))
    response = requests.post(
        TELEX_WEBHOOK_URL,
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )
    print("Telex Response:", response.json())
    return response.json()


@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    The /tick endpoint triggers the MySQL health check as a background task,
    returns the results in JSON format, and includes a message: 'Check your Telex channel'.
    """
    try:
        # Run the MySQL check in the background and also get the result synchronously using run_in_executor.
        loop = asyncio.get_running_loop()
        status = await loop.run_in_executor(None, get_mysql_status)
        background_tasks.add_task(send_to_telex)
        return JSONResponse(status_code=202, content={
            "mysql_status": status,
            "message": "Check your Telex channel"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/integration.json")
def get_integration_json(request: Request):
    """
    Returns the integration JSON that Telex uses to configure the integration.
    """
    try:
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
                    "app_url": "https://mysql-performance-monitor.onrender.com",
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
                        "label": "interval",
                        "type": "text",
                        "required": "true",
                        "default": "*/5 * * * *"
                    }
                ],
                "target_url": "https://mysql-performance-monitor.onrender.com/tick",
                "tick_url": "https://mysql-performance-monitor.onrender.com/tick"
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Failed to generate integration JSON"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    uvicorn.run(app, host="127.0.0.1", port=port)
