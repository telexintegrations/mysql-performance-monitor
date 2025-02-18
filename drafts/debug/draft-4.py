import pymysql
import httpx
import asyncio
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from os import getenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Fetch Telex Webhook URL from environment
TELEX_WEBHOOK_URL = getenv("TELEX_WEBHOOK_URL")

# Fetch MySQL Credentials from environment
MYSQL_HOST = getenv("MYSQL_HOST")
MYSQL_USER = getenv("MYSQL_USER")
MYSQL_PASSWORD = getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = getenv("MYSQL_DATABASE")
MYSQL_PORT = getenv("MYSQL_PORT", 3306)

app = FastAPI()
executor = ThreadPoolExecutor()


# Define Pydantic Models
class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str


class MonitorPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: list[Setting]


# Check MySQL Server Health
def check_mysql_health(host: str, user: str, password: str, database: str, port: int = 3306):
    print(f"Connecting to MySQL at {host} with user {user}:...")
    health = {}
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Connected to MySQL successfully")
        with connection.cursor() as cursor:
            # cursor.execute("SHOW GLOBAL STATUS")
            # status_data = cursor.fetchall()
            # Check MySQL version:
            cursor.execute("SELECT VERSION() AS version;")
            version = cursor.fetchone()
            health['MySQL Version'] = version['version'] if version else 'Unknown'

            # Returns Database Name:
            cursor.execute("SELECT DATABASE() AS dbname;")
            dbname = cursor.fetchone()
            health['Database Name'] = dbname['dbname'] if dbname else 'Unknown'

            # # Check Open Tables:
            # cursor.execute("SHOW OPEN TABLES;")
            # open_tables = cursor.fetchall()
            # # List only table names
            # health['Open Tables'] = [row['Table'] for row in open_tables] if open_tables else []

            # Check Uptime (seconds):
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
            uptime = cursor.fetchone()
            health['Uptime (sec)'] = uptime['Value'] if uptime else 'Unknown'

            # Check Slow Queries:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
            slow_queries = cursor.fetchone()
            health['Slow Queries'] = slow_queries['Value'] if slow_queries else 'Unknown'

            # Check Threads Connected:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
            threads_connected = cursor.fetchone()
            health['Threads Connected'] = threads_connected['Value'] if threads_connected else 'Unknown'

            # Check Total Connections:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
            connections = cursor.fetchone()
            health['Total Connections'] = connections['Value'] if connections else 'Unknown'

            # Check Current Open Connections:
            # Using the processlist count as current open connections
            cursor.execute("SELECT COUNT(*) AS current_open_connections FROM information_schema.processlist;")
            open_conn = cursor.fetchone()
            health['Current Open Connections'] = open_conn['current_open_connections'] if open_conn else 'Unknown'

            # Check Query Cache Hits:
            cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
            qcache_hits = cursor.fetchone()
            health['Query Cache Hits'] = qcache_hits['Value'] if qcache_hits else 'Unknown'

            # Check Running Processes & Queries:
            cursor.execute("SHOW FULL PROCESSLIST;")
            processes = cursor.fetchall()
            # We'll include basic info for each process
            health['Running Processes & Queries'] = processes
        connection.close()
        return health
        # return {"status": "healthy", "data": status_data}

    except pymysql.MySQLError as e:
        print(f"MySQL Connection Error: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}


def get_mysql_status():
    health = {}

    try:
        # Establish connection
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=3306,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # Check MySQL version:
            cursor.execute("SELECT VERSION() AS version;")
            version = cursor.fetchone()
            health['MySQL Version'] = version['version'] if version else 'Unknown'

            # Returns Database Name:
            cursor.execute("SELECT DATABASE() AS dbname;")
            dbname = cursor.fetchone()
            health['Database Name'] = dbname['dbname'] if dbname else 'Unknown'

            # # Check Open Tables:
            # cursor.execute("SHOW OPEN TABLES;")
            # open_tables = cursor.fetchall()
            # # List only table names
            # health['Open Tables'] = [row['Table'] for row in open_tables] if open_tables else []

            # Check Uptime (seconds):
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
            uptime = cursor.fetchone()
            health['Uptime (sec)'] = uptime['Value'] if uptime else 'Unknown'

            # Check Slow Queries:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
            slow_queries = cursor.fetchone()
            health['Slow Queries'] = slow_queries['Value'] if slow_queries else 'Unknown'

            # Check Threads Connected:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
            threads_connected = cursor.fetchone()
            health['Threads Connected'] = threads_connected['Value'] if threads_connected else 'Unknown'

            # Check Total Connections:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
            connections = cursor.fetchone()
            health['Total Connections'] = connections['Value'] if connections else 'Unknown'

            # Check Current Open Connections:
            # Using the processlist count as current open connections
            cursor.execute("SELECT COUNT(*) AS current_open_connections FROM information_schema.processlist;")
            open_conn = cursor.fetchone()
            health['Current Open Connections'] = open_conn['current_open_connections'] if open_conn else 'Unknown'

            # Check Query Cache Hits:
            cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
            qcache_hits = cursor.fetchone()
            health['Query Cache Hits'] = qcache_hits['Value'] if qcache_hits else 'Unknown'

            # Check Running Processes & Queries:
            cursor.execute("SHOW FULL PROCESSLIST;")
            processes = cursor.fetchall()
            # We'll include basic info for each process
            health['Running Processes & Queries'] = processes

        connection.close()
        return health

    except pymysql.MySQLError as err:
        return {
            "error": str(err),
            "status": "failure"
        }


def send_to_telex():
    mysql_status = get_mysql_status()

    payload = {
        "event_name": "MySQL Server Health Check",
        "message": f"MySQL Server Health Status:\n"
                   f"Uptime: {mysql_status.get('uptime', 'N/A')} seconds\n"
                   f"Threads Connected: {mysql_status.get('threads_connected', 'N/A')}\n"
                   f"Total Queriesssss: {mysql_status.get('total_queries', 'N/A')}",
        "status": mysql_status["status"],
        "username": "server-monitor"
    }

    response = requests.post(
        TELEX_WEBHOOK_URL,
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )

    print("Response:", response.json())


# Background Task for Monitoring
async def monitor_task(payload: MonitorPayload):
    settings_dict = {s.label: s.default for s in payload.settings}
    mysql_host = settings_dict.get("MySQL Host")
    mysql_user = settings_dict.get("MySQL User")
    mysql_password = settings_dict.get("MySQL Password")
    mysql_database = settings_dict.get("MySQL Database")

    print(f"Monitoring MySQL at {mysql_host}")
    health = await asyncio.get_running_loop().run_in_executor(
        executor, check_mysql_health, mysql_host, mysql_user, mysql_password, mysql_database
    )
    print("Health Check Results:", health)
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(payload.return_url, json=health, headers=headers)
        print(f"Telex Response: {response.status_code}, {response.text}")


# Tick Endpoint to Trigger Monitoring
@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    try:
        if request.method == "POST":
            payload = await request.json()
            print("Received Payload:", payload)
            monitor_payload = MonitorPayload.parse_obj(payload)
        else:
            monitor_payload = MonitorPayload(
                channel_id="mysql-performance-monitor",
                return_url="https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e",
                settings=[
                    Setting(label="MySQL Host", type="text", required=True, default=getenv("MYSQL_HOST")),
                    Setting(label="MySQL User", type="text", required=True, default=getenv("MYSQL_USER")),
                    Setting(label="MySQL Password", type="text", required=True, default=getenv("MYSQL_PASSWORD")),
                    Setting(label="MySQL Database", type="text", required=True, default=getenv("MYSQL_DATABASE")),
                ],
            )
        print("Monitor Payload:", monitor_payload)
        background_tasks.add_task(monitor_task, monitor_payload)
        send_to_telex()
        return JSONResponse(status_code=202, content={"message": "Monitoring started"})
    except Exception as e:
        print(f"Tick Endpoint Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Integration JSON Endpoint
@app.get("/integration.json")
def get_integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")
    print(f"Base URL: {base_url}")
    try:
        integration_json = {
            "data": {
                "descriptions": {
                    "app_name": "MySQL Performance Monitor",
                    "app_description": "Monitors a remote MySQL server for new log messages and posts them to the Telex channel.",
                    "app_url": base_url,
                    "app_logo": "https://banner2.cleanpng.com/20180404/ytq/avh7i6zoc.webp",
                    "background_color": "#fff"
                },
                "integration_type": "interval",
                "settings": [
                    {
                        "label": "mysql_host",
                        "type": "text",
                        "required": True,
                        "default": "Remote MySQL Host"
                    },
                    {
                        "label": "mysql_user",
                        "type": "text",
                        "required": True,
                        "default": "Remote MySQL User"
                    },
                    {
                        "label": "mysql_password",
                        "type": "text",
                        "required": True,
                        "default": "Cannot be disclosed"
                    },
                    {
                        "label": "mysql_database",
                        "type": "text",
                        "required": True,
                        "default": "Database is remote"
                    },
                    {
                        "label": "interval",
                        "type": "text",
                        "required": True,
                        "default": "* * * * *"
                    }
                ],
                "target_url": "",
                "tick_url": f"{base_url}/tick"
            }
        }
        return integration_json
    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Failed to generate integration JSON"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
