import requests

url = "https://ping.telex.im/v1/webhooks/01951646-7c0f-7f5b-9aa4-ec674d2f666e"
payload = {
    "event_name": "string",
    "message": "python post",
    "status": "success",
    "username": "collins"
}

response = requests.post(
    url,
    json=payload,
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
)
print(response.json())