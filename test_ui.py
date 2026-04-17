import urllib.request
import json
try:
    req = urllib.request.Request('http://localhost:8000/chats')
    response = urllib.request.urlopen(req)
    print("Chats:", response.read().decode('utf-8'))
except Exception as e:
    print("Error fetching chats:", e)
