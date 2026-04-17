from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    status = Column(String(50), default="Active")
    db_config = Column(JSON, nullable=True) # Specialized DB config for RAG
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Extensibility field for new project features
    extra_data = Column(JSON, nullable=True)

    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="project", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String(255))
    path = Column(String(512))
    type = Column(String(100))
    category = Column(String(100), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for doc-specific features
    metadata_json = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="documents")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    extra_data = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(36), ForeignKey("chats.id"))
    role = Column(String(50)) # 'user' or 'ai'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # For source citations, token counts, etc.
    metadata_json = Column(JSON, nullable=True)

    chat = relationship("Chat", back_populates="messages")

class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
