import pymysql
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MySQL Connection Credentials
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "test_db")

# Telex Webhook URL
TELEX_WEBHOOK_URL = "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e"

def get_mysql_status():
    try:
        # Establish connection using PyMySQL
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        
        # Fetch MySQL server status
        cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
        uptime = cursor.fetchone()

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
        threads_connected = cursor.fetchone()

        cursor.execute("SHOW GLOBAL STATUS LIKE 'Queries';")
        total_queries = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "uptime": uptime["Value"] if uptime else "Unknown",
            "threads_connected": threads_connected["Value"] if threads_connected else "Unknown",
            "total_queries": total_queries["Value"] if total_queries else "Unknown",
            "status": "success"
        }
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
                   f"Total Queries: {mysql_status.get('total_queries', 'N/A')}",
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

# Run the function
send_to_telex()
