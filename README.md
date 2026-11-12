# NexaMind AI

One workspace for chat, research, agents, and automation — built on DeepSeek Harness.

## What this is

**NexaMind AI** is a production-oriented AI platform: a FastAPI backend, a React/Vite/Tailwind frontend, and an SQLite/PostgreSQL data layer. It covers:

- Chat with persistent, exportable conversations (streaming, models, citations)
- Global News (BBC/Al Jazeera RSS + Tavily AI search & summaries)
- AI Command Center (task decomposition → agent assignment → execution → synthesis)
- Global Knowledge Graph (entity/relationship storage)
- Software Development Workspace (public GitHub repo inspection)
- Web search + Deep Research (Tavily)
- URL analysis and document intelligence (PDF/DOCX/XLSX/CSV/TXT/images)
- Image analysis/generation, video generation with AI voiceover (Replicate)
- Media gallery
- Multi-agent orchestration (quantum, healthcare, finance, cybersecurity)
- Chatbot Studio + RAG (local embeddings; pgvector-capable)
- Automation workflows with approval gates
- AI evaluation benchmarking
- MCP connection management
- API Universe (2,359 public APIs)
- Ollama local model inference
- Google Sign-In + Forgot Password
- AI DevOps dashboard and audit logging
- Authentication (JWT), RBAC, rate limiting, SSRF-safe URL fetching

## Repository layout

```
nexamind/
├── backend/
│   ├── app/                  # FastAPI application
│   │   ├── config.py         # Environment-driven settings (no secrets logged)
│   │   ├── database.py       # Async SQLAlchemy engine/session
│   │   ├── models.py         # ORM models (users, chats, agents, workflows, …)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── security.py       # bcrypt + JWT
│   │   ├── deps.py           # Authentication dependencies
│   │   ├── middleware.py     # Rate limiting + CORS
│   │   ├── logging_buffer.py # In-memory log ring buffer
│   │   ├── services/         # OpenRouter, search, fetch, docs, RAG, agents, …
│   │   └── routers/          # API route groups
│   ├── requirements.txt
│   └── data/                 # SQLite DB + storage (created at runtime)
├── frontend/
│   ├── src/                  # React + Vite + Tailwind
│   └── dist/                 # Built artifacts (served by the backend)
├── .env.example              # Copy to .env and fill in real secrets
├── REQUIREMENTS_TRACKER.md   # Requirement → implementation/test status
└── README.md                 # this file
```

## Prerequisites

- Python 3.12+ (recommended) with pip
- Node.js 24+ and npm 11+ (frontend)
- Optional but recommended for full features:
  - PostgreSQL server (SQLite works out of the box)
  - Tesseract binary for image OCR (`tesseract`)
  - Tavily API key for web search / Deep Research
  - Hugging Face token for HF inference
  - Replicate API token for video generation
  - WABT, jq, JADX/JADX-MCP-JAR, TShark — used by optional REA-style sidecars; not required by NexaMind itself
  - Firebase service-account credentials (optional) to use Firestore as the primary database

## Quick start (local development)

### 1. Clone/enter the project

```powershell
cd C:\Users\LENOVO\Documents\deepseek-harness\default-workspace\nexamind
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ..\..\.env.example .env      # or create backend/.env manually
# Edit .env: set OPENROUTER_API_KEY and any optional keys
python -m uvicorn app.main:app --reload --port 8000
```

Backend API: `http://127.0.0.1:8000`  
Health: `http://127.0.0.1:8000/health`

### 3. Frontend

```powershell
cd ../frontend
npm install
npm run build   # produces dist/ (served by FastAPI at /)
npm run dev     # Vite dev server proxies /api to http://127.0.0.1:8000
```

Frontend dev server: `http://127.0.0.1:5173` (proxies API to port 8000)  
Production: the backend serves `frontend/dist/` automatically at `/`.

### 4. First login

Register at `/login`. The **first registered account becomes the workspace administrator**.

## Google Sign-In (optional)

NexaMind supports **Continue with Google**. It requires a Google OAuth Web Client ID.
See **[GOOGLE_SIGNIN_SETUP.md](GOOGLE_SIGNIN_SETUP.md)** for the 2-minute setup.

- Frontend: `VITE_GOOGLE_CLIENT_ID` in `frontend/.env`
- Backend: `GOOGLE_CLIENT_ID` in `backend/.env`
- Authorized origins: `http://localhost:5173` and `http://127.0.0.1:8000`

## Configuration

Copy `.env.example` to `.env` and set real values. Never commit `.env`.

| Variable | Purpose | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | LLM chat/completions (required for chat, agents, RAG answers, eval) | (none) |
| `OPENROUTER_BASE_URL` | OpenRouter endpoint | `https://openrouter.ai/api/v1` |
| `TAVILY_API_KEY` | Web search / Deep Research | (none) |
| `REPLICATE_API_TOKEN` | Video generation | (none) |
| `EMBEDDING_PROVIDER` | `local` (offline) or `openrouter` | `local` |
| `GHIDRA_INSTALL_DIR` | Ghidra 12.x for native analysis sidecar | (none) |
| `JADX_MCP_JAR`, `REA_WABT_BIN_DIRECTORY`, … | Optional REA providers | (none) |
| `FIREBASE_PROJECT_ID` | Firebase project ID (optional primary DB) | (none) |
| `FIREBASE_CREDENTIALS_PATH` | Path to service-account JSON (optional primary DB) | (none) |
| `FIREBASE_BUCKET` | Firebase storage bucket (optional) | (none) |

## Firebase (optional)

NexaMind AI can use **Firestore** as its primary database when you provide Firebase credentials.

1. Create a Firebase project at https://console.firebase.google.com
2. Create a Cloud Storage bucket (optional)
3. Generate a **Service Account Key** and download the JSON file
4. Set `FIREBASE_PROJECT_ID` and `FIREBASE_CREDENTIALS_PATH` in your `.env`
5. Restart the backend

Firestore status will appear in `GET /health` and `GET /api/devops/integrations`.

Secrets are **never** returned by `/api/devops/config` and are never written to logs or the frontend.

## Running tests

### Backend

```powershell
cd backend
python -m pytest -q
```

### Frontend

```powershell
cd frontend
npx vitest run
```

## Deployment

The backend serves the built frontend from `frontend/dist/`. For a containerized deploy:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend ./backend
COPY frontend/dist ./frontend/dist
RUN pip install -r backend/requirements.txt
ENV DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/nexamind
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- Set `DATABASE_URL` to PostgreSQL for production.
- Set `SECRET_KEY` to a strong random value.
- Behind TLS, restrict `CORS_ORIGINS` to your domain.
- Run migrations if you introduce schema changes: `alembic revision --autogenerate` + `alembic upgrade head`.

## What’s covered vs. what still needs credentials

See `REQUIREMENTS_TRACKER.md` for per-requirement status. In short:

- ✅ Core chat, auth, agents, workflows, evaluation, media, MCP, knowledge/RAG, DevOps
- ⚠️ OpenRouter chat works when `OPENROUTER_API_KEY` is set; otherwise endpoints return `integration_not_configured`
- ⚠️ Web search needs `TAVILY_API_KEY`
- ⚠️ Video generation needs `REPLICATE_API_TOKEN`
- ⚠️ Hugging Face needs `HF_TOKEN`
- ⚠️ OCR needs the system `tesseract` binary

## Security notes

- API keys live only on the backend (`.env` / environment), never in frontend code or browser storage.
- URL fetching is SSRF-guarded: localhost, private/reserved IPs, credentials in URLs, and blocked ports are rejected.
- File uploads are validated by extension and size; stored outside the web root where possible.
- MCP tool calls require explicit per-connection approval when enabled.

## License

Internal DeepSeek Harness sample application.
