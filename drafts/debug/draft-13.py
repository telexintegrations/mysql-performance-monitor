import pymysql
import httpx
import asyncio
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
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
MYSQL_PORT = int(getenv("MYSQL_PORT", 3306))

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
def check_mysql_health():
    health = {}
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version;")
            version = cursor.fetchone()
            health['MySQL Version'] = version['version'] if version else 'Unknown'

            cursor.execute("SELECT DATABASE() AS dbname;")
            dbname = cursor.fetchone()
            health['Database Name'] = dbname['dbname'] if dbname else 'Unknown'

            cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
            uptime = cursor.fetchone()
            health['Uptime (sec)'] = uptime['Value'] if uptime else 'Unknown'

            cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
            threads_connected = cursor.fetchone()
            health['Threads Connected'] = threads_connected['Value'] if threads_connected else 'Unknown'

            cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
            connections = cursor.fetchone()
            health['Total Connections'] = connections['Value'] if connections else 'Unknown'

            cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
            slow_queries = cursor.fetchone()
            health['Slow Queries'] = slow_queries['Value'] if slow_queries else 'Unknown'

            cursor.execute("SHOW FULL PROCESSLIST;")
            processes = cursor.fetchall()
            health['Running Processes & Queries'] = len(processes)

        connection.close()
        return health

    except pymysql.MySQLError as e:
        return {"status": "unhealthy", "error": str(e)}


# Function to send MySQL status to Telex
async def send_to_telex():
    if not TELEX_WEBHOOK_URL:
        print("TELEX_WEBHOOK_URL is not set. Skipping Telex notification.")
        return

    mysql_status = check_mysql_health()

    # Construct message for Telex
    message = (
        f"MySQL Server Health Status:\n"
        f"Database: {mysql_status.get('Database Name', 'N/A')}\n"
        f"MySQL Version: {mysql_status.get('MySQL Version', 'N/A')}\n"
        f"Uptime: {mysql_status.get('Uptime (sec)', 'N/A')} sec\n"
        f"Threads Connected: {mysql_status.get('Threads Connected', 'N/A')}\n"
        f"Total Connections: {mysql_status.get('Total Connections', 'N/A')}\n"
        f"Slow Queries: {mysql_status.get('Slow Queries', 'N/A')}\n"
        f"Running Queries: {mysql_status.get('Running Processes & Queries', 'N/A')}\n"
    )

    payload = {
        "event_name": "MySQL Server Health Check",
        "message": message,
        "username": "server-monitor"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            response.raise_for_status()
            print("Telex response:", response.json())
        except httpx.HTTPError as err:
            print(f"Error sending Telex notification: {err}")


# Background Task for Monitoring
async def monitor_task(payload: MonitorPayload):
    print(f"Monitoring MySQL at {MYSQL_HOST}")
    health = await asyncio.get_running_loop().run_in_executor(executor, check_mysql_health)
    print("Health Check Results:", health)

    # Send results to Telex
    await send_to_telex()


@app.get("/health-check")
async def health_check(background_tasks: BackgroundTasks):
    """Endpoint to trigger MySQL health check and send report to Telex."""
    background_tasks.add_task(send_to_telex)
    return {"message": "MySQL health check is running in the background."}

