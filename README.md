<!-- # mysql-performance-monitor
Effective monitoring tool designed to track the health and performance of MySQL databases in real time -->

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

Feel free to reach out for any improvements or issues! 🚀

