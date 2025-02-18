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
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Connected to MySQL successfully.\n\nFetching MySQL Server Health Status...")
        with connection.cursor() as cursor:
            # cursor.execute("SHOW GLOBAL STATUS")
            # status_data = cursor.fetchall()
            # Check MySQL version:
            cursor.execute("SELECT VERSION() AS version;")
            version = cursor.fetchone()
            # health['MySQL Version'] = version['version'] if version else 'Unknown'

            # Returns Database Name:
            cursor.execute("SELECT DATABASE() AS dbname;")
            dbname = cursor.fetchone()
            # health['Database Name'] = dbname['dbname'] if dbname else 'Unknown'

            # # Check Open Tables:
            # cursor.execute("SHOW OPEN TABLES;")
            # open_tables = cursor.fetchall()
            # # List only table names
            # health['Open Tables'] = [row['Table'] for row in open_tables] if open_tables else []

            # Check Uptime (seconds):
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
            uptime = cursor.fetchone()
            # health['Uptime (sec)'] = uptime['Value'] if uptime else 'Unknown'

            # Check Slow Queries:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
            slow_queries = cursor.fetchone()
            # health['Slow Queries'] = slow_queries['Value'] if slow_queries else 'Unknown'

            # Check Threads Connected:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
            threads_connected = cursor.fetchone()
            # health['Threads Connected'] = threads_connected['Value'] if threads_connected else 'Unknown'

            # Check Total Connections:
            cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
            connections = cursor.fetchone()
            # health['Total Connections'] = connections['Value'] if connections else 'Unknown'

            # Check Current Open Connections:
            # Using the processlist count as current open connections
            cursor.execute("SELECT COUNT(*) AS current_open_connections FROM information_schema.processlist;")
            open_conn = cursor.fetchone()
            # health['Current Open Connections'] = open_conn['current_open_connections'] if open_conn else 'Unknown'

            # Check Query Cache Hits:
            cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
            qcache_hits = cursor.fetchone()
            # health['Query Cache Hits'] = qcache_hits['Value'] if qcache_hits else 'Unknown'

            # Check Running Processes & Queries:
            # cursor.execute("SHOW FULL PROCESSLIST;")
            # processes = cursor.fetchall()
            # We'll include basic info for each process
            # health['Running Processes & Queries'] = processes

            cursor.close()
            connection.close()
            # return health

        return {
            "version": version["Value"] if version else "Unknown",
            "dbname": dbname["Value"] if dbname else "Unknown",
            "uptime": uptime["Value"] if uptime else "Unknown",
            "slow_queries": slow_queries["Value"] if slow_queries else "Unknown",
            "threads_connected": threads_connected["Value"] if threads_connected else "Unknown",
            "connections": connections["Value"] if connections else "Unknown",
            "open_conn": open_conn["Value"] if open_conn else "Unknown",
            "qcache_hits": qcache_hits["Value"] if qcache_hits else "Unknown",
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
    
    print(payload.get("message"))

    response = requests.post(
        TELEX_WEBHOOK_URL,
        json=payload.get("message"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )

    print(response.json())

# Run the function
send_to_telex()
