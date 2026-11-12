"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.split("@")[-1] or " " in value:
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: int
    email: str
    name: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)


# ---------- chat ----------
class ConversationCreate(BaseModel):
    title: str = Field(default="New chat", max_length=200)
    model: str = Field(default="", max_length=160)
    system_prompt: str = ""


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=160)
    system_prompt: str | None = None
    archived: bool | None = None


class MessageOut(ORMModel):
    id: int
    role: str
    content: str
    model: str
    tokens_in: int
    tokens_out: int
    cost: float
    citations: list[dict[str, Any]] = []
    error: str | None = None
    created_at: datetime


class ConversationOut(ORMModel):
    id: int
    title: str
    model: str
    system_prompt: str
    archived: bool
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ChatRequest(BaseModel):
    conversation_id: int
    content: str = Field(min_length=1, max_length=100_000)
    model: str | None = None
    regenerate: bool = False
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=32000)


class SelfCritiqueModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ---------- models ----------
class ModelOut(ORMModel):
    id: int
    provider: str
    model_id: str
    name: str
    context_window: int
    input_price: float
    output_price: float
    capabilities: dict[str, Any] = {}
    enabled: bool


# ---------- search / research ----------
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=6, ge=1, le=12)


class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    answer: str | None = None
    results: list[SearchResult]
    provider: str
    latency_ms: int


class ResearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    depth: Literal["quick", "standard", "deep"] = "standard"


class ResearchOut(ORMModel):
    id: int
    question: str
    plan: list[str]
    report: str
    sources: list[dict[str, Any]]
    status: str
    created_at: datetime


class UrlAnalyzeRequest(BaseModel):
    url: str
    question: str | None = None


class UrlAnalyzeResponse(BaseModel):
    url: str
    title: str
    text: str
    summary: str
    answer: str | None = None
    links: list[str] = []
    fetched_bytes: int


# ---------- documents / media ----------
class DocumentOut(ORMModel):
    id: int
    knowledge_base_id: int
    filename: str
    mime_type: str
    size: int
    status: str
    error: str | None
    meta: dict[str, Any] = {}
    created_at: datetime


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""


class KnowledgeBaseOut(ORMModel):
    id: int
    name: str
    description: str
    created_at: datetime


class RagQuery(BaseModel):
    knowledge_base_id: int
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Literal["semantic", "hybrid"] = "hybrid"


class RagHit(BaseModel):
    document_id: int
    filename: str
    chunk_id: int
    content: str
    score: float


class RagResponse(BaseModel):
    query: str
    hits: list[RagHit]
    answer: str | None = None
    citations: list[dict[str, Any]] = []
    mode: str


class MediaOut(ORMModel):
    id: int
    kind: str
    title: str
    mime_type: str
    size: int
    source: str
    meta: dict[str, Any] = {}
    created_at: datetime


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    model: str = Field(default="", max_length=160)
    n: int = Field(default=1, ge=1, le=4)


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    model: str = Field(default="", max_length=160)
    duration_seconds: int = Field(default=30, ge=6, le=3600)
    language: str = Field(default="English", max_length=40)
    voice_id: str | None = Field(default=None, max_length=120)


class CropParams(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 640
    height: int = 360


class VideoEditRequest(BaseModel):
    source_media_id: int
    trim_start: float | None = None
    trim_end: float | None = None
    resize_width: int | None = None
    crop: CropParams | None = None
    speed: float | None = Field(default=None, gt=0, le=10)
    volume: float | None = Field(default=None, ge=0, le=10)
    overlay_text: str | None = Field(default=None, max_length=500)
    overlay_position: str = Field(default="bottom", max_length=20)
    overlay_fontsize: int = Field(default=48, ge=8, le=300)


class VideoConcatRequest(BaseModel):
    media_ids: list[int] = Field(min_length=2, max_length=50)


class ImageQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    model: str = Field(default="", max_length=160)


# ---------- agents ----------
class AgentOut(ORMModel):
    id: int
    slug: str
    name: str
    domain: str
    description: str
    model: str
    tools: list[str] = []
    restrictions: list[str] = []
    enabled: bool


class AgentRunRequest(BaseModel):
    agent_slug: str | None = None
    input: str = Field(min_length=1, max_length=20000)
    model: str | None = None
    use_tools: bool = True


class AgentExecutionOut(ORMModel):
    id: int
    agent_id: int
    input: str
    output: str
    model: str
    status: str
    error: str | None
    tokens_in: int
    tokens_out: int
    cost: float
    latency_ms: int
    log: list[dict[str, Any]] = []
    created_at: datetime


# ---------- workflows ----------
class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    graph: dict[str, Any] = Field(default_factory=dict)


class WorkflowOut(ORMModel):
    id: int
    name: str
    description: str
    graph: dict[str, Any]
    version: int
    active: bool
    created_at: datetime


class WorkflowRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionOut(ORMModel):
    id: int
    workflow_id: int
    status: str
    input: dict[str, Any]
    output: dict[str, Any]
    logs: list[dict[str, Any]]
    error: str | None
    approval_token: str | None
    created_at: datetime


class ApprovalRequest(BaseModel):
    token: str
    approved: bool


# ---------- chatbots ----------
class ChatbotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    instructions: str = ""
    model: str = ""
    knowledge_base_id: int | None = None
    grounded: bool = True
    theme: dict[str, Any] = Field(default_factory=dict)


class ChatbotOut(ORMModel):
    id: int
    name: str
    instructions: str
    model: str
    knowledge_base_id: int | None
    grounded: bool
    public_token: str
    published: bool
    theme: dict[str, Any] = {}


class ChatbotTestRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


# ---------- mcp ----------
class MCPCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    require_approval: bool = True
    allow_private: bool = False


class MCPOut(ORMModel):
    id: int
    name: str
    url: str
    allowed_tools: list[str]
    require_approval: bool
    allow_private: bool
    enabled: bool
    status: str
    tools: list[dict[str, Any]]
    last_error: str | None
    last_checked: datetime | None


class MCPCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


# ---------- evaluation ----------
class EvalDatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    items: list[dict[str, Any]] = Field(min_length=1)


class EvalDatasetOut(ORMModel):
    id: int
    name: str
    items: list[dict[str, Any]]
    created_at: datetime


class EvalRunRequest(BaseModel):
    dataset_id: int
    model: str
    max_items: int = Field(default=10, ge=1, le=100)


class EvalRunOut(ORMModel):
    id: int
    dataset_id: int
    model: str
    status: str
    metrics: dict[str, Any]
    results: list[dict[str, Any]]
    error: str | None
    created_at: datetime


# ---------- misc ----------
class UsageOut(BaseModel):
    tokens_in: int
    tokens_out: int
    cost: float
    requests: int


class IntegrationStatus(BaseModel):
    provider: str
    configured: bool
    detail: str


class HFInferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    model: str = ""
    max_tokens: int = Field(default=256, ge=1, le=4096)


class HealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, str]


TokenResponse.model_rebuild()
