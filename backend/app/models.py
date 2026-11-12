"""SQLAlchemy ORM models for NexaMind AI."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="New chat", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="openai/gpt-4o-mini", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )

    __table_args__ = (Index("ix_conversations_user_updated", "user_id", "updated_at"),)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system | tool
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AIModel(Base, TimestampMixin):
    __tablename__ = "ai_models"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), default="openrouter", nullable=False)
    model_id: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # USD / 1M tokens
    output_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UploadedFile(Base, TimestampMixin):
    __tablename__ = "uploaded_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream", nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="document", nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class MediaItem(Base, TimestampMixin):
    __tablename__ = "media_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # image | video | document | audio
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="upload", nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    domain: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    tools: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    restrictions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AgentExecution(Base, TimestampMixin):
    __tablename__ = "agent_executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    input: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    log: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    graph: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WorkflowExecution(Base, TimestampMixin):
    __tablename__ = "workflow_executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    logs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Chatbot(Base, TimestampMixin):
    __tablename__ = "chatbots"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    knowledge_base_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="SET NULL"))
    grounded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    theme: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_bases"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)

    __table_args__ = (UniqueConstraint("document_id", "idx", name="uq_chunk_doc_idx"),)


class EvaluationDataset(Base, TimestampMixin):
    __tablename__ = "evaluation_datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class MCPConnection(Base, TimestampMixin):
    __tablename__ = "mcp_connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    headers_encrypted: Mapped[str] = mapped_column(Text, default="", nullable=False)
    allowed_tools: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class APIUsage(Base):
    __tablename__ = "api_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    endpoint: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    provider: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ResearchRun(Base, TimestampMixin):
    __tablename__ = "research_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    report: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
