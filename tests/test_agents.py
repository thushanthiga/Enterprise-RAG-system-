import pytest
from agents.sql_agent import SQLAgent

@pytest.fixture
def sql_agent():
    return SQLAgent()

def test_sql_extraction(sql_agent):
    raw_llm = "Here is the SQL: ```sql\nSELECT * FROM users;\n```"
    sql = sql_agent._extract_sql(raw_llm)
    assert sql == "SELECT * FROM users;"

def test_sql_validation_safe(sql_agent):
    sql = "SELECT name FROM employees WHERE id = 1"
    error = sql_agent._validate_sql(sql, "hr")
    assert error is None

def test_sql_validation_unsafe_keyword(sql_agent):
    sql = "DELETE FROM employees"
    error = sql_agent._validate_sql(sql, "hr")
    assert "Blocked keyword detected" in error or "Only SELECT allowed" in error

def test_sql_validation_unsafe_type(sql_agent):
    sql = "DROP TABLE employees"
    error = sql_agent._validate_sql(sql, "hr")
    assert "Only SELECT allowed" in error or "Blocked keyword detected" in error

def test_sql_trim_schema(sql_agent):
    long_schema = "A" * 4000
    trimmed = sql_agent._trim_schema(long_schema, max_chars=100)
    assert len(trimmed) <= 120 # 100 + suffix
    assert "[... truncated]" in trimmed
