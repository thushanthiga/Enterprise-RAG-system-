import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def api_client():
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock()
    orchestrator.ask = AsyncMock(return_value={
        "answer": "This is a mock answer",
        "intent": "sql",
        "source": "erp",
        "sql": "SELECT * FROM mock_table",
        "total_rows": 5
    })
    orchestrator.ask_stream = MagicMock()
    
    async def mock_stream(*args, **kwargs):
        tokens = ["This", " is", " a", " mock", " stream"]
        for token in tokens:
            yield token
            
    orchestrator.ask_stream.side_effect = mock_stream
    return orchestrator

@pytest.fixture(autouse=True)
def patch_orchestrator(monkeypatch, mock_orchestrator):
    # Patch the global orchestrator instance in app.main
    import app.main
    app.main.orchestrator = mock_orchestrator
    yield mock_orchestrator
    app.main.orchestrator = None

@pytest.fixture
def mock_httpx_client(respx_mock):
    # For testing BaseAgent logic
    return respx_mock
