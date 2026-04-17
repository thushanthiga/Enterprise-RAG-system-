"""Legacy wrapper — re-exports from agents.router_agent."""
from agents.router_agent import RouterAgent, classify_intent  # noqa: F401

# Convenience function matching the original blueprint signature
async def classify_intent(question: str) -> dict:
    router = RouterAgent()
    return await router.classify(question)
