"""
This Python code checks the status of a
remote MySQL server using PyMySQL.
"""
# Import statements
import pymysql
from os import getenv


def check_mysql_health(host, user, password, database, port=3306):
    """
    Connects to the MySQL server using PyMySQL and runs a series of health-check commands
    in the specified order. Returns a dictionary with the results.
    """
    health = {}

    try:
        # Establish connection
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
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

    except Exception as e:
        return {"error": str(e)}


if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Replace these with your actual MySQL server credentials
    host = getenv("MYSQL_HOST")
    user = getenv("MYSQL_USER")
    password = getenv("MYSQL_PASSWORD")
    database = getenv("MYSQL_DATABASE")

    health_status = check_mysql_health(host, user, password, database)

    print("MySQL Server Health Status:")
    for key, value in health_status.items():
        if key == "Running Processes & Queries":
            print(f"\n{key}:")
            for process in value:
                print(process)
        else:
            print(f"{key}: {value}")


# def check_mysql_health(host, user, password, database, port=3306):
#     """
#     Connects to the MySQL server using PyMySQL and runs several status commands
#     to assess its health.

#     Parameters:
#         host (str): Hostname or IP address of the MySQL server.
#         user (str): MySQL username.
#         password (str): MySQL password.
#         database (str): Database name (required for connection).
#         port (int): Port number for MySQL (default: 3306).

#     Returns:
#         dict: A dictionary with various health status metrics.
#     """
#     health = {}

#     try:
#         # Establish a connection to the MySQL server
#         connection = pymysql.connect(
#             host=host,
#             user=user,
#             password=password,
#             database=database,
#             port=port,
#             cursorclass=pymysql.cursors.DictCursor
#         )

#         with connection.cursor() as cursor:

#             # Check MySQL version
#             cursor.execute("SELECT VERSION();")
#             qcache_hits = cursor.fetchone()
#             health['Query Cache Hits'] = qcache_hits['Value'] if qcache_hits else 'Unknown'

#             # Check server uptime
#             cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
#             uptime = cursor.fetchone()
#             health['Uptime (sec)'] = uptime['Value'] if uptime else 'Unknown'

#             # Check number of slow queries
#             cursor.execute("SHOW GLOBAL STATUS LIKE 'Slow_queries';")
#             slow_queries = cursor.fetchone()
#             health['Slow Queries'] = slow_queries['Value'] if slow_queries else 'Unknown'

#             # Check current number of connected threads
#             cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected';")
#             threads_connected = cursor.fetchone()
#             health['Threads Connected'] = threads_connected['Value'] if threads_connected else 'Unknown'

#             # Check number of threads that are running
#             cursor.execute("SHOW GLOBAL STATUS LIKE 'Threads_running';")
#             threads_running = cursor.fetchone()
#             health['Threads Running'] = threads_running['Value'] if threads_running else 'Unknown'

#             # Check total number of connection attempts
#             cursor.execute("SHOW GLOBAL STATUS LIKE 'Connections';")
#             connections = cursor.fetchone()
#             health['Connections'] = connections['Value'] if connections else 'Unknown'

#             # Check query cache hits (if applicable)
#             cursor.execute("SHOW STATUS LIKE 'Qcache_hits';")
#             qcache_hits = cursor.fetchone()
#             health['Query Cache Hits'] = qcache_hits['Value'] if qcache_hits else 'Unknown'

#         connection.close()
#         return health

#     except Exception as e:
#         return {"error": str(e)}


# if __name__ == '__main__':
#     from dotenv import load_dotenv
#     load_dotenv()


#     # Replace these with your remote MySQL server credentials
#     host = getenv("MYSQL_HOST")
#     user = getenv("MYSQL_USER")
#     password = getenv("MYSQL_PASSWORD")
#     database = getenv("MYSQL_DATABASE")

#     health_status = check_mysql_health(host, user, password, database)

#     print("MySQL Server Health Status:")
#     for key, value in health_status.items():
#         print(f"{key}: {value}")