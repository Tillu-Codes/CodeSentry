# CodeSentry

A full-stack Python bug & security scanner. Deterministic rules (Bandit, detect-secrets,
custom SQL-injection / bare-except / mutable-defaults / inefficiency detectors) with a
pluggable LLM layer for enrichment, GitHub repo & zip ingestion, real-time SSE streaming,
a 3D results visualization, and optional Supabase auth with per-user scan history.

| Phase | What it added |
| --- | --- |
| 1 | Rule engine + `/scan` snippet endpoint, risk scoring |
| 2 | Pluggable LLM enrichment (Groq / Gemini / Ollama / mock) |
| 3 | GitHub + zip repo ingestion, background jobs, progress polling |
| 4 | React + Vite + Tailwind frontend (Monaco editor, results panel) |
| 5 | Supabase auth + persisted scan history (JWT-verified API) |
| 6 | "Wow" layer: React Three Fiber viz, Framer Motion polish, live SSE streaming |
| 7 | Deployment: frontend → Vercel, backend → Render |

## Architecture

```
frontend (Vite/React)  --HTTPS-->  Vercel  --fetch /scan, /scans, SSE-->  Render (FastAPI+uvicorn)
   |                                         ^
   +-- supabase-js (auth) --> Supabase ----+   (auth token passed as Bearer; persisted via service-role key)
```

- **Backend**: `backend/` — FastAPI, `uvicorn`, threads for parallel scanning, `queue`-based
  SSE event bus, pluggable storage (`SupabaseStore` / in-memory fallback).
- **Frontend**: `frontend/` — Vite, React 19, TypeScript, Tailwind, zustand, Monaco,
  react-three-fiber, framer-motion.

## Local development

Backend (defaults to rules-only when no keys are set):

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # fill in LLM / Supabase keys as needed
uvicorn main:app --reload       # http://127.0.0.1:8000
```

Frontend (proxies `/api` → `http://127.0.0.1:8000`):

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                     # http://localhost:5173
```

Tests: `python -m pytest` in `backend/` · lint/build: `npm run lint` / `npm run build` in `frontend/`.

## Deploying

### 1. Backend → Render

1. Push this repository to GitHub.
2. In [Render](https://render.com): **New → Blueprint**, select the repo. It will read
   `render.yaml` (Docker image via `backend/Dockerfile`, health check on `/health`).
3. Fill in the secret env vars flagged `sync: false` (see table below) in the Render
   dashboard: **Environment** tab → *New Environment Variable*.
4. Note the backend URL: `https://codesentry-backend.onrender.com`.

### 2. Frontend → Vercel

1. In [Vercel](https://vercel.com): **Add New Project**, import the same repo.
   `frontend/vercel.json` sets the root directory and build/output (`dist`).
2. Add these env vars (Settings → Environment Variables), then deploy:

| Variable | Example |
| --- | --- |
| `VITE_API_BASE` | `https://codesentry-backend.onrender.com` |
| `VITE_SUPABASE_URL` | `https://xyz.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | your Supabase anon key |

3. Set `CORS_ORIGINS` on the Render backend to your Vercel origin
   (e.g. `https://codesentry.vercel.app`) and redeploy the backend service.

### 3. Supabase

1. Create a project; copy the project URL, `service_role` key, and the JWT secret
   (`Settings → API`; the JWT secret lives in `Settings → API → JWT Secret`).
2. Run the migration `backend/supabase/migrations/001_init.sql` in the SQL editor
   (creates `scans`/`findings` tables + row-level security).
3. Add users in **Authentication → Users** (or via the sign-up form in the app).

## Environment variables

### Backend (`render.yaml` / `backend/.env`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | no | `groq` \| `gemini` \| `ollama` \| `mock`; unset = rules-only |
| `GROQ_API_KEY` | no | Groq key (default provider) |
| `GROQ_MODEL` | no | default `llama-3.3-70b-versatile` |
| `GEMINI_API_KEY` | no | Gemini key |
| `GEMINI_MODEL` | no | default `gemini-2.0-flash` |
| `OLLAMA_URL` / `OLLAMA_MODEL` | no | local Ollama endpoint |
| `SUPABASE_URL` | no | enables persistence |
| `SUPABASE_SERVICE_ROLE_KEY` | no | server-side DB access |
| `SUPABASE_JWT_SECRET` | no | enables auth (JWT verification) |
| `CORS_ORIGINS` | no | comma-separated frontend origins; empty = `*` |

### Frontend (`Vercel` / `frontend/.env`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `VITE_API_BASE` | prod | backend URL; empty in dev uses the Vite `/api` proxy |
| `VITE_SUPABASE_URL` | no | disables auth UI when empty |
| `VITE_SUPABASE_ANON_KEY` | no | Supabase anon key |

## API overview

- `POST /scan` — create a snippet scan job (`ScanJob` with `scan_id`)
- `GET /scan/{scan_id}` — poll job state
- `GET /scan/{scan_id}/events` — SSE stream: `snapshot`, `progress`, `file` findings, `done`
- `POST /scan/repo`, `POST /scan/repo/zip` — GitHub repo / zip-archive scans (same SSE)
- `GET /scans`, `GET /scans/{scan_id}`, `DELETE /scans/{scan_id}`, `GET /me` — auth-only history
- `GET /health` — health check used by Render
