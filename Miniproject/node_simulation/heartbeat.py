import requests
import time
import sys

API_URL = "http://localhost:5000/heartbeat"

if len(sys.argv) < 2:
    print("Usage: python3 heartbeat.py <node_id>")
    sys.exit(1)

node_id = sys.argv[1]

while True:
    try:
        res = requests.post(API_URL, json={"node_id": node_id})
        # Log full response to verify what server returns
        print(f"[Heartbeat] Sent: {res.json()}")  # Debugging the response
    except Exception as e:
        print("Error:", e)
    time.sleep(3)  # every 3 sec
