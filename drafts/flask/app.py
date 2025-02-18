from flask import Flask, jsonify, request
import mysql.connector
import os
import threading
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route('/integration.json', methods=['GET'])
def integration_json():
    base_url = request.url_root.rstrip('/')
    data = {
        "data": {
            "descriptions": {
                "app_name": "MySQL Log Monitor",
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
    return jsonify(data)

@app.route('/tick', methods=['POST'])
def tick():
    payload = request.get_json()
    # Process the task in a separate thread to avoid blocking the request
    threading.Thread(target=monitor_task, args=(payload,)).start()
    return jsonify({"status": "accepted"}), 202

def monitor_task(payload):
    # Extract settings from the payload
    settings = payload.get("settings", [])
    settings_dict = {setting["label"]: setting["default"] for setting in settings}
    last_log_id = int(settings_dict.get("last_log_id", "0"))

    # Connect to the remote MySQL server
    try:
        connection = mysql.connector.connect(
            host=settings_dict.get("mysql_host"),
            user=settings_dict.get("mysql_user"),
            password=settings_dict.get("mysql_password"),
            database=settings_dict.get("mysql_database")
        )
        cursor = connection.cursor(dictionary=True)
        query = "SELECT id, log_message, created_at FROM mysql_logs WHERE id > %s ORDER BY id ASC"
        cursor.execute(query, (last_log_id,))
        logs = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as e:
        send_to_telex(payload.get("return_url"), f"Failed to connect or fetch logs: {str(e)}")
        return

    if logs:
        messages = []
        for log in logs:
            messages.append(f"[{log['created_at']}] {log['log_message']}")
            last_log_id = log["id"]
        message = "\n".join(messages)
        send_to_telex(payload.get("return_url"), message)
    else:
        print("No new logs found.")

def send_to_telex(return_url, message):
    # Prepare the payload in the Telex webhook format
    data = {
        "message": message,
        "username": "MySQL Log Monitor",
        "event_name": "MySQL Log Update",
        "status": "info"
    }
    try:
        response = requests.post(return_url, json=data)
        if response.status_code == 200:
            print("Message sent successfully")
        else:
            print(f"Failed to send message: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending message to Telex: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
