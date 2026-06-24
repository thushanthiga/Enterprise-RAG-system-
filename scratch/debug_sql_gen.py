import asyncio
from app.database import get_db, SessionLocal
from app import models
from sqlalchemy import select
from agents.orchestrator_agent import OrchestratorAgent

async def main():
    agent = OrchestratorAgent()
    async with SessionLocal() as db:
        result = await db.execute(select(models.Project).where(models.Project.id == 6))
        project = result.scalar_one_or_none()
        cfg = project.db_config[0] if isinstance(project.db_config, list) else project.db_config
        db_url = f"mysql+aiomysql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"

        # set manual db_schema_text so we hit the LLM logic
        db_schema_text = "Table: users | Columns: id, name, created_at"

        res = await agent.ask(
            question="how many tables are here",
            search_mode="db",
            project_id=6,
            db_url=db_url,
            db_schema_text=db_schema_text
        )
        print("RESULT:")
        import pprint
        pprint.pprint(res)

if __name__ == "__main__":
    asyncio.run(main())
