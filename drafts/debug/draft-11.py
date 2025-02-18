from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import mysql.connector
import httpx
import asyncio
from app.config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

app = FastAPI()

@app.get("/integration.json")
def get_integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {
        "data": {
            "descriptions": {
                "app_name": "MySQL Log Monitor",
                "app_description": "Monitors a remote MySQL server for new log messages and posts them to the Telex channel.",
                "app_url": base_url,
                "app_logo": "https://i.imgur.com/lZqvffp.png",
                "background_color": "#fff"
            },
            "integration_type": "interval",
            "settings": [
                {
                    "label": "mysql_host",
                    "type": "text",
                    "required": True,
                    "default": MYSQL_HOST or "your-mysql-host"
                },
                {
                    "label": "mysql_user",
                    "type": "text",
                    "required": True,
                    "default": MYSQL_USER or "your-username"
                },
                {
                    "label": "mysql_password",
                    "type": "text",
                    "required": True,
                    "default": MYSQL_PASSWORD or "your-password"
                },
                {
                    "label": "mysql_database",
                    "type": "text",
                    "required": True,
                    "default": MYSQL_DATABASE or "your-database"
                },
                {
                    "label": "last_log_id",
                    "type": "text",
                    "required": False,
                    "default": "0"
                },
                {
                    "label": "interval",
                    "type": "text",
                    "required": True,
                    "default": "* * * * *"
                }
            ],
            "tick_url": f"{base_url}/tick"
        }
    }


# Pydantic models for the payload
class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str


class MonitorPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: List[Setting]


def connect_db(settings: List[Setting]):
    settings_dict = {s.label: s.default for s in settings}
    connection = mysql.connector.connect(
        host=settings_dict.get("mysql_host"),
        user=settings_dict.get("mysql_user"),
        password=settings_dict.get("mysql_password"),
        database=settings_dict.get("mysql_database")
    )
    return connection


def fetch_new_logs(connection, last_log_id: int):
    cursor = connection.cursor(dictionary=True)
    query = "SELECT id, log_message, created_at FROM mysql_logs WHERE id > %s ORDER BY id ASC"
    cursor.execute(query, (last_log_id,))
    logs = cursor.fetchall()
    cursor.close()
    return logs


async def send_to_telex(return_url: str, message: str):
    payload = {
        "message": message,
        "username": "MySQL Log Monitor",
        "event_name": "MySQL Log Update",
        "status": "info"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(return_url, json=payload)
        if response.status_code == 200:
            print("Message sent successfully")
        else:
            print(f"Failed to send message: {response.status_code}, {response.text}")


async def monitor_task(payload: MonitorPayload):
    settings_dict = {s.label: s.default for s in payload.settings}
    last_log_id = int(settings_dict.get("last_log_id", "0"))

    try:
        connection = connect_db(payload.settings)
    except Exception as e:
        error_message = f"Failed to connect to MySQL: {str(e)}"
        await send_to_telex(payload.return_url, error_message)
        return

    try:
        logs = fetch_new_logs(connection, last_log_id)
        connection.close()
    except Exception as e:
        error_message = f"Error fetching logs: {str(e)}"
        await send_to_telex(payload.return_url, error_message)
        return

    if logs:
        messages = []
        for log in logs:
            messages.append(f"[{log['created_at']}] {log['log_message']}")
            last_log_id = log["id"]
        message = "\n".join(messages)
        await send_to_telex(payload.return_url, message)
    else:
        print("No new logs found.")


@app.post("/tick", status_code=202)
def tick_endpoint(payload: MonitorPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(asyncio.create_task, monitor_task(payload))
    return JSONResponse({"status": "accepted"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
