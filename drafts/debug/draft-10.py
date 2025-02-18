import asyncio
import json
import os
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import pymysql
from os import getenv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Pydantic models for integration settings and payload
class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str

class MonitorPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: List[Setting]

app = FastAPI()

# Configure CORS for allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://staging.telextest.im", 
        "http://telextest.im", 
        "https://staging.telex.im", 
        "https://telex.im"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/logo")
def get_logo():
    return FileResponse("uptime.png")

@app.get("/integration.json")
def get_integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")
    integration_json = {
        "data": {
            "date": {"created_at": "2025-02-09", "updated_at": "2025-02-09"},
            "descriptions": {
                "app_name": "MySQL Performance Monitor",
                "app_description": "Monitors a remote MySQL server for performance metrics and logs.",
                "app_logo": "https://i.imgur.com/lZqvffp.png",
                "app_url": base_url,
                "background_color": "#fff",
            },
            "is_active": True,
            "integration_type": "interval",
            "key_features": [
                "Real-time performance monitoring",
                "Slow query analysis",
                "Resource usage metrics",
                "Alert on critical thresholds"
            ],
            "integration_category": "Monitoring & Logging",
            "website": base_url,
            "settings": [
                {"label": "MySQL Host", "type": "text", "required": True, "default": getenv("MYSQL_HOST")},
                {"label": "MySQL User", "type": "text", "required": True, "default": getenv("MYSQL_USER")},
                {"label": "MySQL Password", "type": "text", "required": True, "default": getenv("MYSQL_PASSWORD")},
                {"label": "MySQL Database", "type": "text", "required": True, "default": getenv("MYSQL_DATABASE")},
                {"label": "interval", "type": "text", "required": True, "default": "* * * * *"}
            ],
            "target_url": "",
            "tick_url": f"{base_url}/tick"
        }
    }
    return integration_json


def check_mysql_health(host: str, user: str, password: str, database: str, port: int = 3306):
    """
    Connects to the MySQL server and runs several health-check commands.
    Returns a dictionary containing health status metrics.
    """
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
        with connection.cursor() as cursor:
            # MySQL Version
            cursor.execute("SELECT VERSION() AS version;")
            version = cursor.fetchone()
            health['MySQL Version'] = version['version'] if version else 'Unknown'
            
            # Database Name
            cursor.execute("SELECT DATABASE() AS dbname;")
            dbname = cursor.fetchone()
            health['Database Name'] = dbname['dbname'] if dbname else 'Unknown'
            
            # Uptime (seconds)
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
            uptime = cursor.fetchone()
            health['Uptime (sec)'] = uptime['Value'] if uptime else 'Unknown'
            
            # Slow Queries
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
            slow_queries = cursor.fetchone()
            health['Slow Queries'] = slow_queries['Value'] if slow_queries else 'Unknown'
            
            # Threads Connected
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
            threads_connected = cursor.fetchone()
            health['Threads Connected'] = threads_connected['Value'] if threads_connected else 'Unknown'
            
            # Total Connections
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
            connections = cursor.fetchone()
            health['Total Connections'] = connections['Value'] if connections else 'Unknown'
            
            # Current Open Connections (from processlist)
            cursor.execute("SELECT COUNT(*) AS current_open_connections FROM information_schema.processlist;")
            open_conn = cursor.fetchone()
            health['Current Open Connections'] = open_conn['current_open_connections'] if open_conn else 'Unknown'
            
            # Query Cache Hits
            cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
            qcache_hits = cursor.fetchone()
            health['Query Cache Hits'] = qcache_hits['Value'] if qcache_hits else 'Unknown'
            
            # Running Processes & Queries
            cursor.execute("SHOW FULL PROCESSLIST;")
            processes = cursor.fetchall()
            health['Running Processes & Queries'] = processes
        connection.close()
        return health
    except Exception as e:
        return {"error": str(e)}

# Asynchronous background task that performs the MySQL health check and sends results to Telex
async def monitor_task(payload: MonitorPayload):
    # Extract MySQL connection details from payload settings
    settings_dict = {s.label: s.default for s in payload.settings}
    mysql_host = settings_dict.get("MySQL Host")
    mysql_user = settings_dict.get("MySQL User")
    mysql_password = settings_dict.get("MySQL Password")
    mysql_database = settings_dict.get("MySQL Database")
    
    # Run the synchronous MySQL check in a thread pool
    from fastapi.concurrency import run_in_threadpool
    health = await run_in_threadpool(check_mysql_health, mysql_host, mysql_user, mysql_password, mysql_database)
    
    # Format the health check results as a message
    message_lines = []
    for key, value in health.items():
        if key == "Running Processes & Queries":
            message_lines.append(f"{key}: {len(value)} processes")
        else:
            message_lines.append(f"{key}: {value}")
    message = "\n".join(message_lines)
    
    telex_format = {
        "message": message,
        "username": "MySQL Performance Monitor",
        "event_name": "MySQL Health Check",
        "status": "info" if "error" not in health else "error"
    }
    
    headers = {"Content-Type": "application/json"}
    
    if message:
        async with httpx.AsyncClient() as client:
            await client.post(payload.return_url, json=telex_format, headers=headers)

# Updated tick endpoint to accept both POST and GET requests
@app.api_route("/tick", methods=["GET", "POST"], status_code=202)
async def tick_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Tick endpoint that triggers the MySQL health check.
    For POST requests, it uses the provided payload.
    For GET requests, it constructs a default payload using environment variables and hard-coded defaults.
    """
    if request.method == "POST":
        payload = await request.json()
        # Parse the JSON payload into our MonitorPayload model
        try:
            monitor_payload = MonitorPayload.parse_obj(payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    else:  # For GET requests, construct a default payload for testing
        monitor_payload = MonitorPayload(
            channel_id="mysql-performance-monitor",
            return_url="https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e",
            settings=[
                Setting(label="MySQL Host", type="text", required=True, default=getenv("MYSQL_HOST", "your-mysql-host")),
                Setting(label="MySQL User", type="text", required=True, default=getenv("MYSQL_USER", "your-username")),
                Setting(label="MySQL Password", type="text", required=True, default=getenv("MYSQL_PASSWORD", "your-password")),
                Setting(label="MySQL Database", type="text", required=True, default=getenv("MYSQL_DATABASE", "your-database")),
                Setting(label="interval", type="text", required=True, default="* * * * *")
            ]
        )
    background_tasks.add_task(monitor_task, monitor_payload)
    return JSONResponse({"status": "success"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
