from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from dotenv import load_dotenv

from pathlib import Path

# Load environment variables from config/.env
env_path = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(dotenv_path=env_path)

# Use the environment variable for the application metadata database
SQLALCHEMY_DATABASE_URL = os.getenv("APP_DB_URL", "mysql+aiomysql://root:root1234@localhost/enterprise_rag_app")

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
