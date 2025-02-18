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
                "id": "mysql-performance-monitor",
                "name": "MySQL Performance Monitor",
                "version": "1.0",
                "description": "Monitor MySQL database health and performance",
                "website": "https://mysql-performance-monitor.onrender.com",
                "tick_url": f"{base_url}/tick",
                "settings": [
                    {"label": "MySQL Host", "type": "text", "required": True},
                    {"label": "MySQL User", "type": "text", "required": True},
                    {"label": "MySQL Password", "type": "text", "required": True},
                    {"label": "MySQL Database", "type": "text", "required": True},
                ]
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Failed to generate integration JSON"})


if __name__ == "__main__":
    """ Running the FastAPI application. """
    import uvicorn
    port = int(environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    uvicorn.run(app, host="0.0.0.0", port=port)
