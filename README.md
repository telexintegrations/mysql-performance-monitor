<!--# mysql-performance-monitor
Effective monitoring tool designed to track the health and performance of MySQL databases in real time -->

<!--
# Telex MySQL Performance Monitor

## 📌 Overview
This project integrates with the Telex platform to monitor MySQL server performance. It periodically checks MySQL server metrics and sends updates to Telex via a webhook.

## 🛠 Features
- Fetches MySQL server metrics (uptime, active connections, query performance, etc.)
- Sends real-time monitoring data to Telex
- Provides API endpoints for manual triggering and webhook integration
- Supports environment-based configuration

---

## 🚀 Installation
### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/telex-mysql-monitor.git
cd telex-mysql-monitor
```

### 2️⃣ Set Up a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate  # On Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Variables
Create a `.env` file in the project root and configure the following variables:

```ini
MYSQL_HOST=your-mysql-host
MYSQL_USER=your-mysql-username
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=your-database-name
TELEX_WEBHOOK_URL=https://ping.telex.im/v1/webhooks/YOUR-WEBHOOK-ID
PORT=8000  # Adjust as needed
```

---

## 🏗 Running the Application
To start the FastAPI server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
```

For local testing:
```bash
uvicorn app.main:app --reload --port 8000
```

---

## 📡 API Endpoints
### 🔹 **Trigger MySQL Monitoring**
**Endpoint:** `/tick`
- **Method:** `POST`
- **Description:** Starts monitoring MySQL performance and sends updates to Telex.
- **Example Payload:**
  ```json
  {
    "channel_id": "mysql-performance-monitor",
    "return_url": "https://ping.telex.im/v1/webhooks/YOUR-WEBHOOK-ID",
    "settings": [
      {"label": "MySQL Host", "type": "text", "required": true},
      {"label": "MySQL User", "type": "text", "required": true},
      {"label": "MySQL Password", "type": "text", "required": true},
      {"label": "MySQL Database", "type": "text", "required": true}
    ]
  }
  ```
- **Response:**
  ```json
  {
    "message": "Monitoring started"
  }
  ```

### 🔹 **Integration JSON**
**Endpoint:** `/integration.json`
- **Method:** `GET`
- **Description:** Returns Telex integration metadata.

---

## 🐳 Running with Docker (Optional)
```bash
docker build -t telex-mysql-monitor .
docker run -p 8000:8000 --env-file .env telex-mysql-monitor
```

---

## 📝 License
This project is licensed under the MIT License.

---

## 🔗 Additional Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Telex API Reference](https://telex.im/docs/)
- [MySQL Performance Metrics](https://dev.mysql.com/doc/refman/en/server-status.html)

---

## 🤝 Contributing
1. Fork the repository
2. Create a new branch (`feature-xyz`)
3. Commit your changes
4. Push to your branch
5. Open a Pull Request

Feel free to reach out for any improvements or issues! 🚀 -->


Below is an updated README file that reflects all the changes and improvements made to your FastAPI Telex integration.

---

# MySQL Performance Monitor Integration for Telex

This FastAPI application logs the health status of a remote MySQL server and sends the results to a Telex channel via a user-configured webhook. The integration is designed to be installed on the Telex platform and is configured via a JSON file served at `/integration.json`.

## Features

- **MySQL Health Check:**
  Connects to a remote MySQL server and retrieves key metrics including:
  - MySQL version
  - Database name
  - Uptime
  - Slow queries
  - Threads connected
  - Total connections
  - Current open connections
  - Query cache hits
  - Available tables in the database

- **Telex Integration:**
  Sends the formatted health status message to a Telex channel using a webhook URL provided by the user.

- **User-Supplied Configuration:**
  All sensitive details (MySQL host, user, password, database, and Telex webhook URL) are provided by the user during integration setup via the integration payload. No sensitive information is hardcoded or taken from environment variables.

- **Interval Configuration:**
  The integration supports running on an interval (default set to every 5 minutes, using the cron expression `*/5 * * * *`).

- **Non-blocking Background Processing:**
  The health check is executed in a background task, allowing the `/tick` endpoint to return immediately with the MySQL status.

## Endpoints

### `/integration.json`

Returns the integration configuration used by Telex to set up the application. The JSON configuration includes:
- Metadata (app name, description, logo, website, etc.)
- Required settings for MySQL connection and Telex webhook configuration
- The tick URL that Telex will use to trigger the integration

Example JSON (partial):

```json
{
  "data": {
    "date": {
      "created_at": "2025-02-18",
      "updated_at": "2025-02-18"
    },
    "descriptions": {
      "app_name": "MySQL Performance Monitor",
      "app_description": "Monitors MySQL Databases in real time",
      "app_logo": "https://i.imgur.com/lZqvffp.png",
      "app_url": "https://your-deployed-url",
      "background_color": "#fff"
    },
    "is_active": "true",
    "integration_category": "Monitoring & Logging",
    "integration_type": "interval",
    "key_features": [
      "Monitors a remote MySQL server",
      "Logs MySQL Server health status to the Telex channel"
    ],
    "author": "Dohou Daniel Favour",
    "settings": [
      {
        "label": "MySQL Host",
        "type": "text",
        "required": "true",
        "default": ""
      },
      {
        "label": "MySQL User",
        "type": "text",
        "required": "true",
        "default": ""
      },
      {
        "label": "MySQL Password",
        "type": "text",
        "required": "true",
        "default": ""
      },
      {
        "label": "MySQL Database",
        "type": "text",
        "required": "true",
        "default": ""
      },
      {
        "label": "WebHook URL Configuration",
        "type": "text",
        "required": "true",
        "default": ""
      },
      {
        "label": "interval",
        "type": "text",
        "required": "true",
        "default": "*/5 * * * *"
      }
    ],
    "target_url": "https://your-deployed-url/tick",
    "tick_url": "https://your-deployed-url/tick"
  }
}
```

### `/tick`

Triggers the MySQL health check:
- Accepts both GET and POST requests.
- When triggered, the endpoint schedules a background task that:
  - Uses the user-provided MySQL details to check the server status.
  - Sends the health status message to the Telex channel using the provided webhook URL.
- Also returns a JSON response containing the MySQL status and the message `"Check your Telex channel"`.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/telexintegrations/mysql-performance-monitor
   cd mysql-performance-monitor
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   *Ensure that the following packages are included in your `requirements.txt`:*
   - fastapi
   - uvicorn
   - httpx
   - pymysql
   - python-dotenv

4. **Deploy the Application:**

   You can run the application locally for testing:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 5000
   ```

   When deploying on a platform like Render, ensure you bind to `0.0.0.0` and use the platform's provided `$PORT` environment variable.

## Testing the Integration

To test the integration, use the following `curl` command to trigger the `/tick` endpoint with user-supplied details:


```json

curl --location --request POST 'http://mysql-performance-monitor.onrender.com/tick' --header 'Content-Type: application/json' --data '{
  "channel_id": "mysql-performance-monitor",
  "return_url": "Enter Your Desired Channel's WebHook URL here",
  "settings": [
    {
      "label": "MySQL Host",
      "type": "text",
      "required": true,
      "default": "Enter Your Server's IP Address Here"
    },
    {
      "label": "MySQL User",
      "type": "text",
      "required": true,
      "default": "Enter Your MySQL User Here"
    },
    {
      "label": "MySQL Password",
      "type": "text",
      "required": true,
      "default": "Enter Your MySQL Password Here"
    },
    {
      "label": "MySQL Database",
      "type": "text",
      "required": true,
      "default": "Enter Your MySQL Database Here"
    },
    {
      "label": "WebHook URL Configuration",
      "type": "text",
      "required": true,
      "default": "Enter Your Desired Channel's WebHook URL here"
    },
    {
      "label": "interval",
      "type": "text",
      "required": true,
      "default": "*/5 * * * *"
    }
  ]
}'
```


This command sends a JSON payload with your MySQL connection details and the Telex webhook URL. The `/tick` endpoint will then trigger the health check, send the results to your Telex channel, and return a response indicating that the status was sent.

<br>

<h2 align="center">ScreenshotsOf My Integration</h2>

![Screenshot 1](/Screenshot-1.png)

![Screenshot 2](/Screenshot-2.png)

<br>

## License

[MIT License](LICENSE)

## Author

[Dohou Daniel Favour](https://linktr.ee/dohoudanielfavour)

<!--
```bash
curl --location --request POST 'http://127.0.0.1:5000/tick' \
--header 'Content-Type: application/json' \
--data '{
  "channel_id": "mysql-performance-monitor",
  "return_url": "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e",
  "settings": [
    {
      "label": "MySQL Host",
      "type": "text",
      "required": true,
      "default": "your.mysql.host"
    },
    {
      "label": "MySQL User",
      "type": "text",
      "required": true,
      "default": "your_username"
    },
    {
      "label": "MySQL Password",
      "type": "text",
      "required": true,
      "default": "your_password"
    },
    {
      "label": "MySQL Database",
      "type": "text",
      "required": true,
      "default": "your_database"
    },
    {
      "label": "WebHook URL Configuration",
      "type": "text",
      "required": true,
      "default": "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e"
    },
    {
      "label": "interval",
      "type": "text",
      "required": true,
      "default": "*/5 * * * *"
    }
  ]
}'
```
-->