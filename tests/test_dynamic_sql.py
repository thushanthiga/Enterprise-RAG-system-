import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

from agents.orchestrator_agent import OrchestratorAgent

async def test_dynamic_schema_passing():
    # Mock settings
    settings = {
        "active_llm_provider": "ollama",
        "ollama_url": "http://localhost:11434",
        "ollama_model": "qwen2.5:7b-instruct-q4_K_M"
    }
    
    # Instantiate orchestrator
    orchestrator = OrchestratorAgent(settings=settings)
    
    # Mock the SQLAgent.run to see what it receives
    orchestrator.sql_agent.run = AsyncMock(return_value={"sql": "SELECT 1", "rows": [{"count": 5}], "total_rows": 1})
    orchestrator.synthesiser.synthesise_sql = AsyncMock(return_value="There are 5 interviews.")
    
    question = "how many interviews have been done"
    db_url = "mysql+aiomysql://root:pw@localhost/test"
    db_schema_text = "Table: interviews has column id"
    
    print(f"Testing ask with dynamic schema: '{db_schema_text[:30]}...'")
    
    result = await orchestrator.ask(
        question=question,
        db_url=db_url,
        db_schema_text=db_schema_text,
        search_mode="db",
        project_id=1
    )
    
    # Verify SQL agent was called with the schema text
    orchestrator.sql_agent.run.assert_called_once()
    args, kwargs = orchestrator.sql_agent.run.call_args
    
    received_schema = kwargs.get("db_schema_text")
    if received_schema == db_schema_text:
        print("SUCCESS: Orchestrator correctly passed the dynamic schema to SQLAgent.")
    else:
        print(f"FAILURE: Orchestrator passed '{received_schema}' instead of expected schema.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_dynamic_schema_passing())
