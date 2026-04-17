import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8000/ask/stream',
    data=json.dumps({
        "question": "what is the table here where the all talent pool applicant have been stored",
        "user_id": "dev",
        "project_id": 6,
        "search_mode": "auto"
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        for line in response:
            decoded = line.decode('utf-8').strip()
            if "metadata" in decoded:
                print("RAW METADATA:", decoded)
except Exception as e:
    print("Error:", e)
