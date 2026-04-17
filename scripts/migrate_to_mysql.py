import json
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine, Base, SessionLocal
from app.models import Project, Document, Chat, Message, AppSetting
from sqlalchemy import select

DATA_DIR = Path(__file__).parent.parent / "data"

async def migrate():
    print("🚀 Starting migration from JSON to MySQL...")

    # 1. Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created.")

    async with SessionLocal() as session:
        # 2. Migrate Settings
        settings_path = DATA_DIR / "settings.json"
        if settings_path.exists():
            with open(settings_path) as f:
                data = json.load(f)
                for key, value in data.items():
                    # Check if setting already exists
                    stmt = select(AppSetting).where(AppSetting.key == key)
                    result = await session.execute(stmt)
                    if not result.scalar_one_or_none():
                        setting = AppSetting(key=key, value=value)
                        session.add(setting)
            print("✅ Settings migrated.")

        # 3. Migrate Projects & Documents
        projects_path = DATA_DIR / "projects.json"
        if projects_path.exists():
            with open(projects_path) as f:
                projects_data = json.load(f)
                for p_data in projects_data:
                    # Check if project already exists
                    stmt = select(Project).where(Project.id == p_data.get("id"))
                    result = await session.execute(stmt)
                    if not result.scalar_one_or_none():
                        project = Project(
                            id=p_data.get("id"),
                            name=p_data.get("name"),
                            status=p_data.get("status", "Active"),
                            db_config=p_data.get("db_config"),
                            extra_data={"legacy_db": p_data.get("db"), "databases": p_data.get("databases")}
                        )
                        session.add(project)
                        await session.flush() # Get ID for documents

                        # Migrate Documents for this project
                        for d_data in p_data.get("documents", []):
                            doc = Document(
                                project_id=project.id,
                                name=d_data.get("name"),
                                path=d_data.get("path"),
                                type=d_data.get("type"),
                                category=d_data.get("category", "general"),
                                created_at=datetime.fromisoformat(d_data["created_at"]) if "created_at" in d_data else datetime.utcnow()
                            )
                            session.add(doc)
            print("✅ Projects and Documents migrated.")

        # 4. Migrate Chats & Messages
        chats_path = DATA_DIR / "chats.json"
        if chats_path.exists():
            with open(chats_path) as f:
                chats_data = json.load(f)
                for c_data in chats_data:
                    stmt = select(Chat).where(Chat.id == c_data.get("id"))
                    result = await session.execute(stmt)
                    if not result.scalar_one_or_none():
                        chat = Chat(
                            id=c_data.get("id"),
                            project_id=c_data.get("project_id"),
                            title=c_data.get("title", "New Chat"),
                            created_at=datetime.fromisoformat(c_data["last_message_at"]) if "last_message_at" in c_data else datetime.utcnow()
                        )
                        session.add(chat)
                        await session.flush()

                        # Migrate Messages
                        for m_data in c_data.get("messages", []):
                            # Timestamp normalization
                            ts_str = m_data.get("timestamp", "")
                            if ts_str.endswith("Z"):
                                ts_str = ts_str.replace("Z", "+00:00")
                            try:
                                ts = datetime.fromisoformat(ts_str)
                            except:
                                ts = datetime.utcnow()

                            msg = Message(
                                chat_id=chat.id,
                                role=m_data.get("role"),
                                content=m_data.get("content"),
                                timestamp=ts
                            )
                            session.add(msg)
            print("✅ Chats and Messages migrated.")

        await session.commit()
    print("🎉 Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
