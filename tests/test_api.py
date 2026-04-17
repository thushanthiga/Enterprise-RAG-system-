import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_token():
    payload = {"user_id": "test_user", "role": "admin"}
    response = client.post("/token", json=payload)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_ask_unauthenticated(patch_orchestrator):
    # In development mode, unauthenticated access is allowed as 'dev'/ 'admin'
    # as per get_current_user in app/main.py
    payload = {"question": "What is the total sales?", "user_id": "test_user"}
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mock answer"
    assert data["intent"] == "sql"

def test_ask_with_token(patch_orchestrator):
    # First get a token
    token_resp = client.post("/token", json={"user_id": "real_user", "role": "employee"})
    token = token_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"question": "How many employees?", "user_id": "real_user"}
    response = client.post("/ask", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["answer"] == "This is a mock answer"

def test_ask_stream(patch_orchestrator):
    payload = {"question": "Stream this", "user_id": "test_user"}
    with client.stream("POST", "/ask/stream", json=payload) as response:
        assert response.status_code == 200
        # Check if it's an event stream
        assert "text/event-stream" in response.headers["content-type"]
        # Read the first event
        for line in response.iter_lines():
            if line:
                assert line.startswith("data: ")
                break
