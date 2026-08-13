# ClinicalFlow

ClinicalFlow is a multi-portal healthcare coordination platform. The repository contains a FastAPI backend, a Next.js frontend, PostgreSQL/SQLite migrations, tenant-aware authorization, patient triage and routing, facility operations, appointments, notifications, and deployment configuration.

The application is suitable for local development and controlled pilots. Production use still requires real provider credentials, reviewed clinical content, facility and staff verification, security review, and operational monitoring.

## Repository layout

```text
backend/                 FastAPI application, models, migrations, and tests
frontend/                Next.js application and browser tests
SUPABASE_DEPLOYMENT.md   Supabase, Render, and Vercel deployment runbook
render.yaml              Render service definitions
railway.toml             Railway deployment definition
scripts/                 Operational and backup helpers
```

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- npm
- PostgreSQL for shared or deployed environments
- Git

SQLite is the default local database. It is not suitable for a deployed service because its filesystem is local and ephemeral.

## Local setup

### Backend

From the repository root:

```bash
cd backend
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env  # Windows: Copy-Item .env.example .env
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check the API from another terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"clinicalflow"}
```

For local SQLite, `AUTO_CREATE_SCHEMA=true` is convenient. For PostgreSQL or any shared environment, use `AUTO_CREATE_SCHEMA=false` and apply Alembic migrations explicitly.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local  # Windows: Copy-Item .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000`. The frontend environment must point to the backend, for example:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_BASE_URL=ws://127.0.0.1:8000
```

## Database and migrations

The tracked database source of truth is `backend/migrations/`. Do not commit `.env`, database files, passwords, JWT secrets, provider keys, or exported patient data.

Run migrations from the `backend` directory:

```bash
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m alembic check
```

For a clean local database, stop the backend, remove `backend/clinicalflow.db`, and run the migration command again. Never delete a shared or production database to repair a migration problem.

## Deployments

ClinicalFlow uses separate services:

1. **Supabase** provides managed PostgreSQL storage.
2. **Render** runs the FastAPI backend and optional worker.
3. **Vercel** runs the Next.js frontend.

Read [SUPABASE_DEPLOYMENT.md](SUPABASE_DEPLOYMENT.md) before deploying. The short version is:

### Render backend

- Connect the repository and deploy the `backend` service from `render.yaml`.
- Build command: `pip install -r backend/requirements.txt`.
- Start command: `cd backend && python -m alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Set `DATABASE_URL` to the Supabase PostgreSQL connection string.
- Set `APP_ENVIRONMENT=production`, `AUTO_CREATE_SCHEMA=false`, `AUTH_COOKIE_SECURE=true`, a strong `SESSION_SECRET`, and the exact Vercel origin in `CORS_ORIGINS`.
- Keep test fixtures, demo content, default credentials, and phone-verification bypass disabled in production.
- Verify the Render `/health` URL before connecting the frontend.

### Vercel frontend

- Set the project root directory to `frontend`.
- Build command: `npm run build`.
- Add the backend URL as `NEXT_PUBLIC_API_BASE_URL`.
- Add the secure WebSocket URL as `NEXT_PUBLIC_WS_BASE_URL` when live updates are enabled.
- Redeploy after changing environment variables. Do not put `DATABASE_URL`, Supabase service-role keys, or backend secrets in Vercel `NEXT_PUBLIC_*` variables.

## Verification commands

Backend checks:

```bash
cd backend
PYTHONPATH=$PWD python -m pytest -q
PYTHONPATH=$PWD python -m alembic check
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run build
```

For browser checks, start the backend and frontend first, then run the Playwright suite configured in `frontend/playwright.config.ts`.

## Main routes

- `/` public landing page
- `/pricing` plans and conversion paths
- `/signup` role selection
- `/login` patient sign-in
- `/hospital/login` facility workspace sign-in
- `/dashboard/chat` patient triage
- `/dashboard/queue` patient queue tracking
- `/hospital/queue` facility queue operations
- `/hospital/appointments` facility scheduling
- `/health` backend health check

## Production boundaries

Before a real clinical launch, configure and verify the email/SMS/push/WhatsApp providers, durable outbox worker, Redis, object storage, payment provider webhooks, PostgreSQL RLS and concurrency behavior, monitoring, backups, restore procedures, accessibility, clinical governance, privacy review, penetration testing, and controlled-pilot acceptance.

Do not use demo accounts or fixed passwords outside an isolated test environment. Do not treat triage output as a confirmed diagnosis; a qualified clinician must review clinical decisions.
