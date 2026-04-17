import asyncio
import os
import sys

# Add root to sys.path
sys.path.append(os.getcwd())

from agents.doc_agent import DocumentAgent

async def test_search():
    agent = DocumentAgent()
    print("Testing Hybrid Search...")
    # Simulate a question
    results = await agent.search("What is the main objective of the project?", project_id=1)
    
    print(f"\nFound {len(results)} results:")
    for i, res in enumerate(results):
        print(f"{i+1}. [{res['method']}] (Score: {res['score']:.4f}) {res['text'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_search())
