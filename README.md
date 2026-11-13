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

## Deployment (Firebase Hosting + Cloud Run)

The frontend is deployed to Firebase Hosting; the FastAPI backend runs on Cloud Run.
Firebase Hosting rewrites `/api/**` to the Cloud Run service so the SPA and API share one origin.

### Prerequisites

- Firebase project `nexamindai-427c1` (owner: sdodda073@gmail.com)
- **Blaze plan** enabled (Cloud Run requires pay-as-you-go)
- `gcloud` + `firebase` CLI (or use **Cloud Shell**, which needs no local install)

### One-command deploy (Google Cloud Shell)

Cloud Shell comes pre-authenticated as your Google account — no local install or keys needed.

```bash
# 1. Open Cloud Shell: https://console.cloud.google.com/cloudshell
git clone https://github.com/doddasurendra/Nexamindai.git
cd Nexamindai/backend

# 2. Create env.yaml with your secrets (copy from local .env)
cat > env.yaml << 'EOF'
OPENROUTER_API_KEY: sk-or-...
TAVILY_API_KEY: tvly-...
REPLICATE_API_TOKEN: r8_...
JSON2VIDEO_API_KEY: <your-json2video-key>
GOOGLE_CLIENT_ID: 598...
GOOGLE_CLIENT_SECRET: GOCSPX-...
DEFAULT_MODEL: baidu/ernie-light-dt-1.0-intl
FALLBACK_MODELS: nex-agi/nex-n2.6,google/gemini-4-carbon
OLLAMA_BASE_URL: "http://localhost:11434"
EOF

# 3. Deploy to Cloud Run (builds from backend/Dockerfile)
gcloud run deploy nexamind-api --source . --region asia-south1 \
  --allow-unauthenticated --memory 2Gi --timeout 600 --port 8080 \
  --env-vars-file env.yaml

# 4. Deploy the frontend + hosting rewrite
cd ..
firebase deploy --only hosting --non-interactive
```

After both steps:

- Frontend: **https://nexamindai-427c1.web.app** (and the `/api/*` routes proxy to Cloud Run)
- API: Cloud Run URL shown by the deploy command

### Caveats (honest)

- **Database**: SQLite lives in `/tmp` on each Cloud Run instance. Data resets on redeploy/scale-out.
  For persistent data, provision **Cloud SQL for PostgreSQL** and point `DATABASE_URL` at it.
- **Media files**: same — use a mounted Cloud Storage bucket or GCS for the media directory.
- **Google OAuth**: add `https://nexamindai-427c1.web.app` as an Authorized JavaScript origin in the OAuth client.
- `.env` must **never** be committed — `env.yaml` contains secrets too. Both are gitignored / dockerignored.

### First-time local container test

```powershell
cd backend
docker build -t nexamind-api .
docker run --rm -p 8080:8080 --env-file .env nexamind-api
# → http://localhost:8080/health
```

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
