import pytest
from app.main import create_access_token, get_current_user
from agents.base_agent import BaseAgent
from fastapi import Request

def test_jwt_generation():
    token = create_access_token("test_user", "admin")
    assert isinstance(token, str)
    assert len(token) > 0

def test_parse_llm_json_clean():
    raw = '{"key": "value"}'
    parsed = BaseAgent.parse_llm_json(raw)
    assert parsed == {"key": "value"}

def test_parse_llm_json_markdown():
    raw = '```json\n{"key": "value"}\n```'
    parsed = BaseAgent.parse_llm_json(raw)
    assert parsed == {"key": "value"}

def test_parse_llm_json_garbage():
    raw = 'Here is the result: {"key": "value"} Hope this helps!'
    parsed = BaseAgent.parse_llm_json(raw)
    assert parsed == {"key": "value"}

def test_parse_llm_json_invalid():
    raw = "not json at all"
    with pytest.raises(ValueError):
        BaseAgent.parse_llm_json(raw)
