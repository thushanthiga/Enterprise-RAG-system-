"""
FastAPI entrypoint — thin API layer with JWT auth, health check,
single-shot /ask and streaming /ask/stream endpoints.
"""
from __future__ import annotations

import os
import sys
import json
import urllib.parse
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Request, Body, File, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
from pydantic import BaseModel
from jose import jwt, JWTError

from config import JWT_SECRET, JWT_ALGORITHM
from agents import OrchestratorAgent
from .database import get_db, SessionLocal
from . import models
from sqlalchemy import select, update, insert, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


# ── Lifespan: instantiate orchestrator once ──────────────────────────
orchestrator: Optional[OrchestratorAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    async with SessionLocal() as db:
        settings = await get_app_settings(db)
        orchestrator = OrchestratorAgent(settings=settings)
    
    yield
    orchestrator = None


app = FastAPI(
    title="Enterprise RAG API",
    description="Local LLM + Enterprise RAG — natural language interface for databases and documents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_app_settings(db: AsyncSession):
    result = await db.execute(select(models.AppSetting))
    settings = {s.key: s.value for s in result.scalars().all()}
    if not settings:
        # Fallback to defaults
        from config import OLLAMA_URL, OLLAMA_MODEL
        defaults = {
            "active_llm_provider": "ollama",
            "ollama_url": OLLAMA_URL,
            "ollama_model": OLLAMA_MODEL,
            "ollama_keep_alive": -1,
            "openai_api_key": "",
            "openai_model": "gpt-4o-mini",
            "doc_root": "./data/docs",
            "index_path": "./data/index"
        }
        for k, v in defaults.items():
            db.add(models.AppSetting(key=k, value=v))
        await db.commit()
        return defaults
    return settings

async def save_app_settings(settings: dict, db: AsyncSession):
    for k, v in settings.items():
        stmt = select(models.AppSetting).where(models.AppSetting.key == k)
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = v
        else:
            db.add(models.AppSetting(key=k, value=v))
    await db.commit()

def get_db_url(config: dict) -> str:
    """Construct async SQLAlchemy URL for Postgres or MySQL."""
    # Robust extraction
    db_type = (config.get("type") or "postgresql").lower()
    host = (config.get("host") or "localhost").strip()
    port = str(config.get("port") or "")
    db_user = (config.get("user") or "").strip()
    pw = config.get("password") or ""
    db_name = (config.get("database") or "").strip()
    
    # Auto-detect MySQL by port 3306 if not specified
    if port == "3306" and "postgresql" in db_type:
        db_type = "mysql"
        
    # Construct authority part (user:pw@)
    auth = ""
    if db_user:
        auth = db_user
        if pw:
            # URL-encode password to handle special chars like @
            safe_pw = urllib.parse.quote_plus(pw)
            auth += f":{safe_pw}"
        auth += "@"
        
    if "mysql" in db_type:
        return f"mysql+aiomysql://{auth}{host}:{port or 3306}/{db_name}"
    else:
        return f"postgresql+asyncpg://{auth}{host}:{port or 5432}/{db_name}"


# ── Request / Response Models ────────────────────────────────────────
class AskRequest(BaseModel):
    question: str
    user_id: str = "anon"
    project_id: Optional[int] = None
    chat_id: Optional[str] = None
    search_mode: Optional[str] = "auto"  # auto, db, doc


class AskResponse(BaseModel):
    answer: str
    intent: Optional[str] = None
    source: Optional[str] = None
    sql: Optional[str] = None
    total_rows: Optional[int] = None


class TokenRequest(BaseModel):
    user_id: str
    role: str = "admin"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── JWT helper ───────────────────────────────────────────────────────
def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=8)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def get_current_user(request: Request) -> dict:
    """Extract user from JWT Bearer token. Returns {user_id, role}."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        # Allow unauthenticated access as admin for development
        return {"user_id": "dev", "role": "admin"}
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"user_id": payload["sub"], "role": payload.get("role", "employee")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Endpoints ────────────────────────────────────────────────────────
@app.post("/reindex")
async def reindex(user: dict = Depends(get_current_user)):
    """Manually trigger document re-indexing."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can re-index")
    
    import subprocess
    try:
        # Run scripts/build_index.py
        script_path = str(Path(__file__).parent.parent / "scripts" / "build_index.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        if result.returncode == 0:
            # Reload index in DocAgent
            if orchestrator and orchestrator.doc_agent:
                orchestrator.doc_agent.reload_index()
            return {"status": "success", "output": result.stdout}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": "enterprise-rag",
        "index_loaded": orchestrator.doc_agent.bm25 is not None if orchestrator else False,
    }


@app.post("/token", response_model=TokenResponse)
async def get_token(req: TokenRequest):
    """Issue a JWT token for a user (development helper)."""
    token = create_access_token(req.user_id, req.role)
    return TokenResponse(access_token=token)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Single-shot question → answer."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")

    project_context = None
    db_url = None
    db_schema_text = None
    project_guidelines_text = None
    if req.project_id:
        result = await db.execute(select(models.Project).where(models.Project.id == req.project_id))
        project = result.scalar_one_or_none()
        if project:
            ctx_parts = []
            db_configs = project.db_config or []
            if isinstance(db_configs, dict):
                db_configs = [db_configs]
            
            if db_configs:
                ctx_parts.append(f"Databases: {', '.join([d.get('name', 'DB') for d in db_configs])}")
                cfg = db_configs[0]
                db_url = get_db_url(cfg)
            
            result_docs = await db.execute(select(models.Document).where(models.Document.project_id == req.project_id))
            docs = result_docs.scalars().all()
            if docs:
                ctx_parts.append(f"Documents: {', '.join([doc.name for doc in docs])}")
            
            if ctx_parts:
                project_context = " | ".join(ctx_parts)
            
            # Guidelines from extra_data
            guidelines = (project.extra_data or {}).get("guidelines") if project.extra_data else None
            if guidelines:
                project_guidelines_text = guidelines
    else:
        # Global Chat: Build an overview of all projects
        result_projects = await db.execute(select(models.Project))
        projects = result_projects.scalars().all()
        overview_parts = []
        for p in projects:
            pname = p.name or "Unnamed Project"
            desc = (p.extra_data or {}).get("guidelines") or "No specific guidelines provided."
            overview_parts.append(f"### Project: {pname}\n{desc}\n")
        
        if overview_parts:
            project_context = "AVAILABLE PROJECTS OVERVIEW:\n" + "\n".join(overview_parts)

    history = []
    if req.chat_id:
        result_msgs = await db.execute(
            select(models.Message)
            .where(models.Message.chat_id == req.chat_id)
            .order_by(models.Message.timestamp.asc())
        )
        messages = result_msgs.scalars().all()
        for m in messages:
            history.append({"role": m.role, "content": m.content})

    result = await orchestrator.ask(
        question=req.question,
        user_id=user["user_id"],
        user_role=user["role"],
        db_url=db_url,
        project_context=project_context,
        db_schema_text=db_schema_text,
        project_guidelines_text=project_guidelines_text if req.project_id else None,
        search_mode=req.search_mode,
        project_id=req.project_id,
        history=history
    )
    return AskResponse(
        answer=result["answer"],
        intent=result.get("intent"),
        source=result.get("source"),
        sql=result.get("sql"),
        total_rows=result.get("total_rows"),
    )


@app.post("/ask/stream")
async def ask_stream(req: AskRequest, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Streaming question → answer (Server-Sent Events)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not ready")

    project_context = None
    db_url = None
    db_schema_text = None
    project_guidelines_text = None
    if req.project_id:
        result = await db.execute(select(models.Project).where(models.Project.id == req.project_id))
        project = result.scalar_one_or_none()
        if project:
            ctx_parts = []
            db_configs = project.db_config or []
            if isinstance(db_configs, dict):
                db_configs = [db_configs]
            
            if db_configs:
                ctx_parts.append(f"Databases: {', '.join([d.get('name', 'DB') for d in db_configs])}")
                cfg = db_configs[0]
                db_url = get_db_url(cfg)
            
            result_docs = await db.execute(select(models.Document).where(models.Document.project_id == req.project_id))
            docs = result_docs.scalars().all()
            if docs:
                ctx_parts.append(f"Documents: {', '.join([doc.name for doc in docs])}")
            
            if ctx_parts:
                project_context = " | ".join(ctx_parts)
            
            # Guidelines from extra_data or storage
            guidelines = (project.extra_data or {}).get("guidelines") if project.extra_data else None
            if guidelines:
                project_guidelines_text = guidelines
    else:
        # Global Chat: Build an overview of all projects
        result_projects = await db.execute(select(models.Project))
        projects = result_projects.scalars().all()
        overview_parts = []
        for p in projects:
            pname = p.name or "Unnamed Project"
            desc = (p.extra_data or {}).get("guidelines") or "No specific guidelines provided."
            overview_parts.append(f"### Project: {pname}\n{desc}\n")
        
        if overview_parts:
            project_context = "AVAILABLE PROJECTS OVERVIEW:\n" + "\n".join(overview_parts)

    history = []
    if req.chat_id:
        result_msgs = await db.execute(
            select(models.Message)
            .where(models.Message.chat_id == req.chat_id)
            .order_by(models.Message.timestamp.asc())
        )
        messages = result_msgs.scalars().all()
        for m in messages:
            history.append({"role": m.role, "content": m.content})

    async def event_stream():
        ai_response_text = ""
        async for item in orchestrator.ask_stream(
            question=req.question,
            user_id=user["user_id"],
            user_role=user["role"],
            db_url=db_url,
            project_context=project_context,
            db_schema_text=db_schema_text,
            project_guidelines_text=project_guidelines_text if req.project_id else None,
            search_mode=req.search_mode,
            project_id=req.project_id,
            history=history
        ):
            if isinstance(item, dict) and "metadata" in item:
                yield f"data: {json.dumps(item)}\n\n"
            else:
                ai_response_text += str(item)
                yield f"data: {json.dumps({'token': item})}\n\n"
        
        # Persist messages to chat history if chat_id is provided
        if req.chat_id:
            async with SessionLocal() as async_db:
                # Add User Message
                async_db.add(models.Message(
                    chat_id=req.chat_id,
                    role="user",
                    content=req.question,
                    timestamp=datetime.now()
                ))
                # Add AI Message
                async_db.add(models.Message(
                    chat_id=req.chat_id,
                    role="ai",
                    content=ai_response_text,
                    timestamp=datetime.now()
                ))
                
                # Auto-title update
                result_chat = await async_db.execute(select(models.Chat).where(models.Chat.id == req.chat_id))
                chat = result_chat.scalar_one_or_none()
                if chat:
                    # Count messages to see if it's the first encounter
                    result_count = await async_db.execute(select(models.Message).where(models.Message.chat_id == req.chat_id))
                    msg_count = len(result_count.scalars().all())
                    if msg_count <= 2:
                        chat.title = req.question[:30] + ("..." if len(req.question) > 30 else "")
                
                await async_db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/projects")
async def list_projects(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Fetch projects with documents eagerly loaded to count them
    result = await db.execute(
        select(models.Project).options(selectinload(models.Project.documents))
    )
    projects = result.scalars().all()
    
    enriched_projects = []
    for p in projects:
        # Determine DB summary
        db_summary = "None"
        if p.db_config:
            if isinstance(p.db_config, list) and len(p.db_config) > 0:
                # e.g. "MySQL, PostgreSQL"
                db_summary = ", ".join(set(str(v.get("type", "DB")).capitalize() for v in p.db_config))
            elif isinstance(p.db_config, dict):
                db_summary = str(p.db_config.get("type", "DB")).capitalize()

        enriched_projects.append({
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "docs": len(p.documents),
            "db": db_summary,
            "created_at": p.created_at
        })
    
    return enriched_projects

# ── Chat Management Endpoints ─────────────────────────────────────
@app.get("/chats")
async def list_chats(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Chat).order_by(models.Chat.created_at.desc()))
    chats = result.scalars().all()
    return [{"id": c.id, "title": c.title, "project_id": c.project_id, "last_message_at": c.created_at} for c in chats]

@app.get("/chats/{chat_id}")
async def get_chat(chat_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Chat).where(models.Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Load messages
    result_msgs = await db.execute(select(models.Message).where(models.Message.chat_id == chat_id).order_by(models.Message.timestamp.asc()))
    messages = result_msgs.scalars().all()
    
    return {
        "id": chat.id,
        "title": chat.title,
        "project_id": chat.project_id,
        "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages]
    }

@app.post("/chats")
async def create_chat(project_id: Optional[int] = Body(None, embed=True), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import uuid
    new_id = str(uuid.uuid4())
    new_chat = models.Chat(
        id=new_id,
        title="New Chat",
        project_id=project_id,
        created_at=datetime.utcnow()
    )
    db.add(new_chat)
    await db.commit()
    return {"id": new_id, "title": "New Chat", "project_id": project_id}

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Chat).where(models.Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if chat:
        await db.delete(chat)
        await db.commit()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Chat not found")

@app.get("/projects/{project_id}")
async def get_project(project_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Attach docs
    result_docs = await db.execute(select(models.Document).where(models.Document.project_id == project_id))
    docs = result_docs.scalars().all()
    
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "db_config": project.db_config,
        "documents": docs
    }

@app.post("/projects")
async def create_project(project: dict = Body(...), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_project = models.Project(
        name=project.get("name"),
        status=project.get("status", "Active"),
        db_config=project.get("db_config", {}),
        extra_data=project.get("extra_data", {})
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project

@app.delete("/projects/{project_id}")
async def delete_project(project_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if project:
        await db.delete(project)
        await db.commit()
        
        # Clean up uploads
        upload_dir = Path(__file__).parent.parent / "data" / "uploads" / str(project_id)
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Project not found")

@app.post("/projects/{project_id}/documents/upload")
async def upload_document(
    project_id: int, 
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    category: str = "uploaded",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create project-specific storage
    upload_dir = Path(__file__).parent.parent / "data" / "uploads" / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = upload_dir / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create Document record
    new_doc = models.Document(
        project_id=project_id,
        name=file.filename,
        path=str(dest_path),
        type=file.content_type,
        category=category,
        created_at=datetime.utcnow()
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # Trigger indexing for documents
    if category != "media" and orchestrator:
        background_tasks.add_task(rebuild_index_and_reload)
    
    return new_doc

@app.post("/projects/{project_id}/documents")
async def add_document(project_id: int, doc: dict = Body(...), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_doc = models.Document(
        project_id=project_id,
        name=doc.get("name"),
        path=doc.get("path"),
        type=doc.get("type"),
        category=doc.get("category", "general"),
        created_at=datetime.utcnow()
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return new_doc

@app.delete("/projects/{project_id}/documents/{doc_id}")
async def delete_document(project_id: int, doc_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Document).where(models.Document.id == doc_id, models.Document.project_id == project_id))
    doc = result.scalar_one_or_none()
    if doc:
        await db.delete(doc)
        await db.commit()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Project not found")

@app.post("/projects/{project_id}/db-config")
async def update_db_config(project_id: int, config: dict = Body(...), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.db_config = config
    await db.commit()
    return config

@app.post("/index/reload")
async def reload_index_endpoint(user: dict = Depends(get_current_user)):
    """Hot-reload the BM25 document index without restarting."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if orchestrator:
        orchestrator.doc_agent.reload_index()
    return {"status": "index reloaded"}

@app.post("/projects/{project_id}/databases/test")
async def test_database_connection(project_id: int, config: dict = Body(...), user: dict = Depends(get_current_user)):
    """Try to connect to the database using SQLAlchemy (Async)."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    url = get_db_url(config)
    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "success", "message": "Connection successful!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/projects/{project_id}/databases")
async def list_project_databases(project_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_configs = project.db_config or []
    if isinstance(db_configs, dict):
        return [db_configs]
    return db_configs

@app.post("/projects/{project_id}/databases")
async def add_project_database(project_id: int, config: dict = Body(...), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update project db_config
    # Assuming config contains the new database details
    project.db_config = config
    await db.commit()
    return config

@app.delete("/projects/{project_id}/databases/{db_id}")
async def delete_project_database(project_id: int, db_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # This assumes db_config is a list. If it's a dict, we clear it.
    project.db_config = None
    await db.commit()
    return {"status": "deleted"}

@app.get("/projects/{project_id}/files/{doc_id}")
async def get_project_file(project_id: int, doc_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Document).where(models.Document.id == doc_id, models.Document.project_id == project_id))
    doc = result.scalar_one_or_none()
    if doc:
        file_path = Path(doc.path)
        if file_path.exists():
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="File on disk not found")
    raise HTTPException(status_code=404, detail="Document not found")

@app.get("/projects/{project_id}/markdown/{filename}")
async def get_project_markdown(project_id: int, filename: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if filename not in ["project_guidelines.md", "db_schema.md"]:
        raise HTTPException(status_code=400, detail="Invalid Markdown filename")
    
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    content = ""
    if filename == "project_guidelines.md":
        content = (project.extra_data or {}).get("guidelines", "")
    elif filename == "db_schema.md":
        content = (project.extra_data or {}).get("db_schema", "")
    
    return {"content": content}

class MarkdownUpdate(BaseModel):
    content: str

@app.put("/projects/{project_id}/markdown/{filename}")
async def update_project_markdown(project_id: int, filename: str, update: MarkdownUpdate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    if filename not in ["project_guidelines.md", "db_schema.md"]:
        raise HTTPException(status_code=400, detail="Invalid Markdown filename")
    
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    extra = project.extra_data or {}
    if filename == "project_guidelines.md":
        extra["guidelines"] = update.content
    elif filename == "db_schema.md":
        extra["db_schema"] = update.content
    
    project.extra_data = extra
    await db.commit()
    return {"status": "success"}

def rebuild_index_and_reload():
    """Trigger the build_index script and reload the DocumentAgent."""
    print("Background Task: Rebuilding RAG Index...")
    import subprocess
    try:
        # Run scripts/build_index.py
        script_path = Path(__file__).parent.parent / "scripts" / "build_index.py"
        subprocess.run([sys.executable, str(script_path)], check=True)
        if orchestrator:
            orchestrator.doc_agent.reload_index()
        print("Background Task: Index rebuilt and reloaded.")
    except Exception as e:
        print(f"Background Task Error: {e}")

@app.get("/projects/{project_id}/messages")
async def get_project_messages(project_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # This was a project-specific log which is now likely part of chats/messages
    # For compatibility, returning empty list
    return []

@app.post("/projects/{project_id}/messages")
async def add_project_message(project_id: int, message: dict = Body(...), user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"status": "ignored"}
# ── Settings Management ──────────────────────────────────────────
@app.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await get_app_settings(db)

@app.post("/settings")
async def update_settings(new_settings: dict = Body(...), db: AsyncSession = Depends(get_db)):
    await save_app_settings(new_settings, db)
    # Re-initialize orchestrator with new settings
    global orchestrator
    settings = await get_app_settings(db)
    orchestrator = OrchestratorAgent(settings=settings)
    return {"status": "success", "message": "Settings updated and orchestrator re-initialized"}

@app.get("/ollama/tags")
async def get_ollama_tags(url: str = "http://localhost:11434"):
    import httpx
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{url}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

