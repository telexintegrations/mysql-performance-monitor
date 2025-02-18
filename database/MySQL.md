<!-- # MySQL Server Health

This directory contains commands that can be used to check the health of a MySQL server.

## Basic Server Health
1. `SHOW GLOBAL STATUS LIKE 'Uptime';` - Displays how long the server has been running.
2. `SELECT VERSION();` - Returns the MySQL Server version
3. `SHOW GLOBAL STATUS;` - Lists a variety of server status variables
4. `SHOW VARIABLES;` - Lists configuration variables which can impact performance.

Below is an example of a comprehensive README that documents a wide range of MySQL commands you can use to monitor your server’s health and performance. You can copy, customize, and expand on this as needed.

--->

# MySQL Monitoring Commands Documentation

This document serves as a comprehensive guide to various MySQL commands used for monitoring the health, performance, and configuration of a MySQL server. Whether you’re tracking uptime, slow queries, connection statistics, resource usage, or replication status, this guide covers the essential commands and explains what each one does.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Basic Server Health and Configuration](#basic-server-health-and-configuration)
4. [Performance and Query Monitoring](#performance-and-query-monitoring)
5. [Connection and Resource Monitoring](#connection-and-resource-monitoring)
6. [InnoDB Engine Specific Monitoring](#innodb-engine-specific-monitoring)
7. [Database and Index Information](#database-and-index-information)
8. [Replication Monitoring](#replication-monitoring)
9. [Error Logging and Diagnostics](#error-logging-and-diagnostics)
10. [Additional Useful Commands](#additional-useful-commands)
11. [Using These Commands in Scripts](#using-these-commands-in-scripts)
12. [Conclusion](#conclusion)

---

## Introduction

Monitoring your MySQL server is critical for maintaining optimal performance and identifying issues before they impact your applications. This guide provides a curated list of commands that can be used manually in the MySQL client or programmatically via scripts (e.g., in Python using a MySQL connector).

---

## Prerequisites

- **MySQL Client:** Ensure you have access to a MySQL client (e.g., `mysql` CLI or MySQL Workbench).
- **Permissions:** You should have at least read access to the server status and performance metrics.
- **Performance Schema:** Some commands rely on the Performance Schema being enabled.

---

## Basic Server Health and Configuration

### Check Server Uptime
```sql
SHOW GLOBAL STATUS LIKE 'Uptime';
```
*Returns the number of seconds the server has been running.*

### Check MySQL Version
```sql
SELECT VERSION();
```
*Displays the current MySQL server version.*

### General Server Status
```sql
SHOW GLOBAL STATUS;
```
*Provides a snapshot of various runtime statistics.*

### View Server Configuration Variables
```sql
SHOW VARIABLES;
```
*Lists all server configuration variables which can affect performance.*

### Check Error Log File Location
```sql
SHOW VARIABLES LIKE 'log_error';
```
*Reveals the path to the MySQL error log file for troubleshooting.*

---

## Performance and Query Monitoring

### Slow Queries Count
```sql
SHOW GLOBAL STATUS LIKE 'Slow_queries';
```
*Displays the total number of queries that exceeded the defined slow query threshold.*

### List Running Processes/Queries
```sql
SHOW FULL PROCESSLIST;
```
*Shows detailed information about currently executing queries, including their state and duration.*

### Temporary Table Creation
```sql
SHOW GLOBAL STATUS LIKE 'Created_tmp%';
```
*Tracks the number of temporary tables created, which can indicate inefficient queries.*

### Query Cache Statistics
```sql
SHOW STATUS LIKE 'Qcache%';
```
*Provides details about the query cache performance (if query cache is enabled).*

### Analyzing Statement Performance with Performance Schema
```sql
SELECT *
FROM performance_schema.events_statements_summary_by_digest
ORDER BY COUNT_STAR DESC
LIMIT 10;
```
*Helps identify the most frequently executed or resource-intensive queries.*

---

## Connection and Resource Monitoring

### Total Connections Count
```sql
SHOW GLOBAL STATUS LIKE 'Connections';
```
*Returns the total number of connection attempts (successful or not) since the server started.*

### Current Open Connections
```sql
SHOW GLOBAL STATUS LIKE 'Threads_connected';
```
*Shows how many clients are currently connected to the server.*

### Running Threads
```sql
SHOW GLOBAL STATUS LIKE 'Threads_running';
```
*Displays the number of threads that are actively running (processing a query).*

### Table Locks Information
```sql
SHOW STATUS LIKE 'Table_locks%';
```
*Provides data on table locks, which might indicate contention issues.*

### Open Tables
```sql
SHOW OPEN TABLES;
```
*Lists tables that are currently open in the server’s cache.*

---

## InnoDB Engine Specific Monitoring

### InnoDB Status Report
```sql
SHOW ENGINE INNODB STATUS\G;
```
*Provides a detailed report on InnoDB’s internal workings, including buffer pool usage, locks, transactions, and deadlocks.*

### InnoDB Buffer Pool Statistics (if available)
```sql
SELECT * FROM information_schema.INNODB_BUFFER_POOL_STATS;
```
*Displays statistics about the InnoDB buffer pool, which can be critical for performance tuning.*

---

## Database and Index Information

### Database Sizes
```sql
SELECT table_schema AS 'Database',
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables
GROUP BY table_schema;
```
*Calculates and displays the size of each database in megabytes.*

### List Indexes for a Specific Database
```sql
SELECT table_name, index_name, seq_in_index, column_name
FROM information_schema.statistics
WHERE table_schema = 'your_database_name'
ORDER BY table_name, index_name, seq_in_index;
```
*Provides details about indexes in a specific database, helping you understand index usage and design.*

### Show Table Status (Additional Table-Level Information)
```sql
SHOW TABLE STATUS FROM your_database_name;
```
*Displays detailed information about each table, including row count, average row length, and engine type.*

---

## Replication Monitoring

### Slave Replication Status
```sql
SHOW SLAVE STATUS\G;
```
*If your server is a replication slave, this command gives detailed insight into replication health and any lag issues.*

### Master Replication Information (if applicable)
```sql
SHOW MASTER STATUS;
```
*Provides information about the current binary log file and position on the master server.*

---

## Error Logging and Diagnostics

### Server Error Log File (Revisited)
```sql
SHOW VARIABLES LIKE 'log_error';
```
*Identifies where MySQL is storing error logs, which are vital for diagnosing issues.*

### Viewing Recent Errors
While there’s no direct SQL command to read the error log from within MySQL, you can use OS-level commands such as:
```bash
tail -n 50 /path/to/mysql/error.log
```
*This will show the last 50 lines of the error log for quick diagnostics.*

---

## Additional Useful Commands

### Check Table Fragmentation
```sql
OPTIMIZE TABLE your_table_name;
```
*While primarily used for maintenance, running this command can reveal table fragmentation issues which may affect performance.*

### Show Full Columns of a Table
```sql
SHOW FULL COLUMNS FROM your_table_name;
```
*Displays detailed information about the columns of a table including collation and comments.*

### Count Rows in a Table
```sql
SELECT COUNT(*) FROM your_table_name;
```
*Simple yet essential for understanding table size and detecting unusual growth.*

### List Databases
```sql
SHOW DATABASES;
```
*Lists all databases available on the server.*

### List Tables in a Database
```sql
SHOW TABLES FROM your_database_name;
```
*Lists all tables within a specific database.*

### Check Index Cardinality
```sql
SHOW INDEX FROM your_table_name;
```
*Provides information about the uniqueness and distribution of indexed values.*

---

## Using These Commands in Scripts

You can incorporate these SQL commands into your monitoring scripts using a programming language like Python. For example, using the `mysql-connector-python` library:

```python
import mysql.connector

def connect_db():
    return mysql.connector.connect(
        host="your_host",
        user="your_username",
        password="your_password",
        database="your_database"
    )

def get_uptime():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SHOW GLOBAL STATUS LIKE 'Uptime';")
    uptime = cursor.fetchone()
    print("Uptime:", uptime)
    cursor.close()
    conn.close()

get_uptime()
```

This example demonstrates how to connect to a MySQL server, execute a command, and process the output. You can similarly integrate other commands to build a comprehensive monitoring solution.

---

## Conclusion

This README provides an extensive set of MySQL commands for monitoring the health and performance of your MySQL server. By using these commands, you can gain valuable insights into uptime, query performance, resource usage, replication status, and more. Use these commands as part of your regular maintenance routine or integrate them into an automated monitoring solution for continuous oversight.

Feel free to customize and extend this documentation as needed. Happy monitoring!
