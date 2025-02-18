"""
The main file for the FastAPI application.
This Python module logs the MySQL server health
status to a Telex channel.
"""
# Import Statements
import pymysql
import requests
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
# from pydantic import BaseModel
from starlette.responses import JSONResponse
from dotenv import load_dotenv
import os
from os import getenv, environ
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

app = FastAPI()
# executor = ThreadPoolExecutor()


# # Define Pydantic Models
# class Setting(BaseModel):
#     label: str
#     type: str
#     required: bool
#     default: str


# class MonitorPayload(BaseModel):
#     channel_id: str
#     return_url: str
#     settings: list[Setting]

# MySQL Connection Credentials
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "test_db")

# Telex Webhook URL
TELEX_WEBHOOK_URL = os.getenv("TELEX_WEBHOOK_URL")


def get_mysql_status():
    """
    A function to get the MySQL server health status.

    Returns:
        dict: A dictionary containing the MySQL server health status
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
        print(
            "\n\nConnected to MySQL successfully.\n\nFetching MySQL Server Health Status...")
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
    Sends the MySQL server health status to
    the Telex channel using a webhook.
    """
    mysql_status = get_mysql_status()

    payload = {
        "event_name": "MySQL Server Health Check",
        "message": f"MySQL Server Health Status:\n"
        f"Version: {mysql_status.get('version', 'N/A')}\n"
        f"Database Name: {mysql_status.get('dbname', 'N/A')}\n"
        f"Uptime: {mysql_status.get('uptime', 'N/A')} seconds\n"
        f"Slow Queries: {mysql_status.get('slow_queries', 'N/A')}\n"
        f"Threads Connected: {mysql_status.get('threads_connected', 'N/A')}\n"
        f"Total Connections: {mysql_status.get('connections', 'N/A')}\n"
        f"Current Open Connections: {mysql_status.get('open_conn', 'N/A')}\n",
        # f"Total Queries: {mysql_status.get('total_queries', 'N/A')}",
        "status": mysql_status["status"],
        "username": "server-monitor"
    }

    print(payload.get("message"))

    response = requests.post(
        TELEX_WEBHOOK_URL,
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )
    print(response.json())


# Check MySQL Server Health
# def check_mysql_health(host: str, user: str, password: str, database: str, port: int = 3306):
#     try:
#         connection = pymysql.connect(
#             host=host,
#             user=user,
#             password=password,
#             database=database,
#             port=port,
#             cursorclass=pymysql.cursors.DictCursor
#         )
#         with connection.cursor() as cursor:
#             cursor.execute("SHOW GLOBAL STATUS")
#             status_data = cursor.fetchall()
#         connection.close()
#         return {"status": "healthy", "data": status_data}
#     except pymysql.MySQLError as e:
#         return {"status": "unhealthy", "error": str(e)}

# Background Task for Monitoring
# def monitor_task(payload: MonitorPayload):
#     settings_dict = {s.label: s.default for s in payload.settings}
#     mysql_host = settings_dict.get("MySQL Host")
#     mysql_user = settings_dict.get("MySQL User")
#     mysql_password = settings_dict.get("MySQL Password")
#     mysql_database = settings_dict.get("MySQL Database")
#
#     health = await asyncio.get_running_loop().run_in_executor(
#         executor, check_mysql_health, mysql_host, mysql_user, mysql_password, mysql_database
#     )
#     headers = {"Content-Type": "application/json"}
#     async with httpx.AsyncClient() as client:
#         await client.post(payload.return_url, json=health, headers=headers)


# Tick Endpoint to Trigger Monitoring
@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    The endpoint to trigger the monitoring.
    """
    try:
        send_to_telex()
        return JSONResponse(status_code=202, content={"message": "Monitoring started, and messaged logged to Telex channel."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Integration JSON Endpoint
@app.get("/integration.json")
def get_integration_json(request: Request):
    """
    The endpoint to return the integration JSON.
    """
    base_url = str(request.base_url).rstrip("/")
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
                    "app_logo": "data:image/png;base64,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",
                    "app_url": "https://mysql-performance-monitor.onrender.com",
                    "background_color": "#fff"
                },
                "is_active": true,
                "integration_type": "interval",
                "key_features": [
                    "Monitors a remote MySQL server",
                    "Logs new MySQL Server status to the Telex channel"
                ],
                "author": "Dohou Daniel Favour",
                "settings": [
                    {
                        "label": "MySQL Host",
                        "type": "text",
                        "required": true,
                        "default": ""
                    },
                    {
                        "label": "MySQL User",
                        "type": "text",
                        "required": true,
                        "default": ""
                    },
                    {
                        "label": "MySQL Password",
                        "type": "text",
                        "required": true,
                        "default": ""
                    },
                    {
                        "label": "MySQL Database",
                        "type": "text",
                        "required": true,
                        "default": ""
                    }
                ],
                "target_url": f"{base_url}/tick",
                "tick_url": f"{base_url}/tick"
            }
        }
        # f"{base_url}/tick",
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Failed to generate integration JSON"})


if __name__ == "__main__":
    """ Running the FastAPI application. """
    import uvicorn
    port = int(environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    uvicorn.run(app, host="0.0.0.0", port=port)
