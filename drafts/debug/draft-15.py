import pymysql
import httpx
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from os import getenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

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
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SHOW GLOBAL STATUS")
            status_data = cursor.fetchall()
        connection.close()
        return {"status": "healthy", "data": status_data}
    except pymysql.MySQLError as e:
        return {"status": "unhealthy", "error": str(e)}

# Background Task for Monitoring
async def monitor_task(payload: MonitorPayload):
    settings_dict = {s.label: s.default for s in payload.settings}
    mysql_host = settings_dict.get("MySQL Host")
    mysql_user = settings_dict.get("MySQL User")
    mysql_password = settings_dict.get("MySQL Password")
    mysql_database = settings_dict.get("MySQL Database")

    health = await asyncio.get_running_loop().run_in_executor(
        executor, check_mysql_health, mysql_host, mysql_user, mysql_password, mysql_database
    )
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        await client.post(payload.return_url, json=health, headers=headers)

# Tick Endpoint to Trigger Monitoring
@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    try:
        if request.method == "POST":
            payload = await request.json()
            monitor_payload = MonitorPayload.parse_obj(payload)
        else:
            monitor_payload = MonitorPayload(
                channel_id="mysql-performance-monitor",
                return_url="https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e",
                settings=[
                    Setting(label="MySQL Host", type="text", required=True, default=getenv("MYSQL_HOST", "localhost")),
                    Setting(label="MySQL User", type="text", required=True, default=getenv("MYSQL_USER", "root")),
                    Setting(label="MySQL Password", type="text", required=True, default=getenv("MYSQL_PASSWORD", "")),
                    Setting(label="MySQL Database", type="text", required=True, default=getenv("MYSQL_DATABASE", "test_db")),
                ],
            )
        background_tasks.add_task(monitor_task, monitor_payload)
        return JSONResponse(status_code=202, content={"message": "Monitoring started"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Integration JSON Endpoint
@app.get("/integration.json")
def get_integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")
    try:
        return {
            "id": "mysql-performance-monitor",
            "name": "MySQL Performance Monitor",
            "version": "1.0",
            "description": "Monitor MySQL database health and performance",
            "website": "https://yourwebsite.com",
            "tick_url": f"{base_url}/tick",
            "settings": [
                {"label": "MySQL Host", "type": "text", "required": True},
                {"label": "MySQL User", "type": "text", "required": True},
                {"label": "MySQL Password", "type": "text", "required": True},
                {"label": "MySQL Database", "type": "text", "required": True},
            ]
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Failed to generate integration JSON"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
