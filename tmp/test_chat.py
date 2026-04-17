import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.main import get_app_settings
from agents.orchestrator_agent import OrchestratorAgent

async def test_chat():
    print("Fetching settings from DB...")
    async with SessionLocal() as db:
        settings = await get_app_settings(db)
        print(f"Settings found: {settings.get('ollama_model')}")
        
        print("Initializing OrchestratorAgent...")
        orchestrator = OrchestratorAgent(settings=settings)
        
        print("Testing chat classification (this calls Ollama)...")
        try:
            # We just need to trigger an LLM call. router.classify often calls LLM for fallback.
            # But let's call self.router.classify directly
            question = "What is the capital of France?"
            # Router should use LLM if it doesn't match rules
            res = await orchestrator.router.classify(question, "admin")
            print(f"Classification result: {res}")
            print("SUCCESS: LLM call completed without 404.")
        except Exception as e:
            print(f"FAILURE: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat())
