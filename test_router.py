import asyncio
from agents.router_agent import RouterAgent

async def test():
    router = RouterAgent()
    print("HAS_ML:", router.ml_model is not None)
    
    with open("data/projects/6/db_schema.md") as f:
        schema = f.read()
        
    q = "what is the table here where the all talent pool applicant have been stored"
    res = await router.classify(q, db_schema_text=schema)
    print("App Result:", res)

if __name__ == "__main__":
    asyncio.run(test())
