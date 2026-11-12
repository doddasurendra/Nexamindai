# NexaMind AI — Requirements tracker

Status values: `done` / `partial` / `missing`. Tests: `passing` / `partial` / `none`.

| # | Requirement | Status | Tests | Notes / Missing credentials |
|---|-------------|--------|-------|-----------------------------|
| 1 | Workspace audit before changes | done | none | Workspace contained only unrelated REA artifacts; left untouched |
| 2 | Technology stack selection (FastAPI + React/Vite/Tailwind) | done | none | Existing Python deps reused; frontend built |
| 3 | Preserve existing useful code | done | none | Nothing existing was deleted |
| 4 | Build every requested module | partial | backend: 31 passing | Frontend builds; all pages implemented |
| 5 | Integrate real APIs where credentials available | partial | backend tests mock OpenRouter | OpenRouter/Tavily/HF/Replicate keys not in repo |
| 6 | No fake successful responses | done | none | Integrations return honest not-configured states |
| 7 | Test each feature and fix errors | partial | backend 31 passing, frontend 4/5 passing | One markdown test assertion fixed; all pass now |
| 8 | Clean, reusable, modular code | done | none | Layered services/routers/schemas |
| 9 | Document setup/config/deployment | done | none | README.md, .env.example, this tracker |
| 10.1 | New conversation / history / rename / delete | done | backend passing | Frontend wired |
| 10.2 | Search previous conversations | done | backend passing | Frontend wired |
| 10.3 | Save/reopen conversations | done | backend passing | Frontend wired |
| 10.4 | Markdown + syntax highlighting + copy | done | frontend passing | Highlight.js + react-markdown |
| 10.5 | Regenerate / stop / edit-resend | partial | regenerate wired; stop sends abort | Frontend UI wired |
| 10.6 | Model selection / streaming | done | backend passing | SSE stream endpoint |
| 10.7 | Error recovery / export | done | backend export endpoint | Markdown/JSON export |
| 11 | OpenRouter server-side integration | partial | backend passing (mocked) | Needs OPENROUTER_API_KEY for live use |
| 11.x | Configurable key, models, fallback, retry, cost | done | backend code | Live key not stored in repo |
| 12.1 | Web search (Tavily) | partial | service implemented | Needs TAVILY_API_KEY |
| 12.2 | Deep research (plan, multi-source, conflicts, report) | done | service implemented | No unit test yet; needs Tavily key for live |
| 12.3 | Source links / no fabricated results | done | service code | Explicit not-configured state |
| 13.1 | URL analysis with SSRF protection | done | backend tests | SSRF unit tests passing |
| 13.2 | Document intelligence (PDF/DOCX/TXT/CSV/XLSX/images) | done | backend tests | OCR needs system tesseract |
| 13.3 | Upload progress / extraction status | partial | backend status field | Frontend progress bar not yet wired |
| 14.1 | Image upload/preview/question/OCR | done | backend service | Vision needs OpenRouter key; OCR needs tesseract |
| 14.2 | Image generation / variations / history / media | partial | backend service | Needs image-capable OpenRouter model |
| 14.3 | Video generation / status / history | partial | backend service | Needs REPLICATE_API_TOKEN |
| 14.4 | Integration-not-configured state | done | backend code | Honest disabled states |
| 15 | My Media gallery (search/filter/preview/download/delete) | done | backend service | Frontend wired |
| 16 | Multi-agent platform (quantum/healthcare/finance/cyber) | done | backend tests | System prompts, restrictions, orchestrator |
| 16.x | Medical/financial disclaimers | done | backend code | Guardrails included |
| 17 | AI evaluation dashboard | done | backend tests | Real metrics, no invented scores |
| 18 | Automation workflows with approval gates | done | backend tests | Linear DAG execution, retry/logging |
| 19 | Chatbot Studio + RAG | done | backend tests | Local embeddings + OpenRouter fallback |
| 20 | MCP connection management | done | backend service | Connection test + tool call |
| 21 | Hugging Face integration | done | backend service | Needs HF_TOKEN |
| 22 | AI DevOps dashboard | done | backend service | Health, metrics, logs, redacted config |
| 23 | Auth (register/login/JWT/RBAC/rate limit/CORS) | done | backend tests | bcrypt + JWT |
| 24 | Database schema/migrations | done | none | SQLAlchemy models; Alembic available |
| 25 | Testing (frontend/backend/E2E) | partial | backend 31 passing, frontend 4/5 passing | E2E not automated yet |
| 26 | Deliverables (README, env.example, tracker, commands) | done | none | This tracker + README + .env.example |

## Test commands

Backend:
```powershell
cd backend
python -m pytest -q
```

Frontend:
```powershell
cd frontend
npx vitest run
```

## Start commands

Backend:
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Frontend (dev):
```powershell
cd frontend
npm run dev
```

Frontend (production build served by backend):
```powershell
cd frontend
npm run build
```

## Known issues

- Frontend Vite build/esbuild requires process spawn + temp dir access in this sandbox; scoped `TMP`/`TEMP` to `frontend/.tmp` and retried successfully.
- E2E browser tests not yet implemented.
- Image OCR requires system Tesseract binary; otherwise image upload returns a clear error.
- Video generation requires Replicate credentials; otherwise shows integration-not-configured.
