# SynaptiVerse

Local MVP setup for a multi-portal healthcare coordination platform with a working backend slice for tickets, queue updates, and booking flows.

## What is working now

The repository now includes:

- A FastAPI backend under backend/ with SQLite persistence for local development.
- Ticket creation, ticket listing, escalation, and queue status update endpoints under /api/v1/.
- A tenant-aware WebSocket endpoint for triage updates.
- A Next.js frontend that calls the backend for booking and queue views.

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## Cloud database options

This project runs locally on SQLite by default, but it also supports a hosted PostgreSQL database via `DATABASE_URL`.

Recommended free-tier providers:

- Supabase Postgres — easy setup, Postgres-native, great for teams.
- Neon Postgres — serverless Postgres with a generous free tier.
- Railway Postgres — simple deployment, quick prototyping.
- Fly.io Postgres — good for apps already on Fly.
- PlanetScale MySQL — possible if you prefer MySQL, but Postgres is the recommended path.

For team collaboration, each developer can use local SQLite or point to a shared cloud database by setting `DATABASE_URL` in their env.

## 1. Start the backend

The backend supports local SQLite by default and can be overridden with `DATABASE_URL` for hosted databases.

Install dependencies and apply the current schema first:

```bash
cd backend
python -m pip install -r requirements.txt
PYTHONPATH=$PWD python -m alembic upgrade head
```

For deployed/shared databases, set `AUTO_CREATE_SCHEMA=false`; local SQLite may keep it enabled for convenience.

From the repository root:

```bash
cd backend
PYTHONPATH=$PWD /usr/local/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

To use a custom database URL, set `DATABASE_URL` first:

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
PYTHONPATH=$PWD /usr/local/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

To use the example env file, copy it and edit the values:

```bash
cd backend
cp .env.example .env
```

If you want to verify that the API is up, open another terminal and run:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"synaptiverse"}
```

## 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open the UI at:

```text
http://127.0.0.1:3000
```

## 3. Test the ticket and queue flow

### Option A: Use the booking form

Open:

```text
http://127.0.0.1:3000/book
```

Fill in:

- Patient phone
- Chief complaint

Submit the form. This sends a request to the backend and creates a ticket.

Then open:

```text
http://127.0.0.1:3000/clinic/queue
```

or

```text
http://127.0.0.1:3000/dashboard/queue
```

You should see the new ticket appear in the queue list.

### Option B: Use the API directly

Create a ticket:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/tickets \
  -H 'Content-Type: application/json' \
  -d '{"customer_phone":"+2348000000000","raw_intake_text":"I have chest pain","channel":"WEB"}'
```

Authenticate and save the HttpOnly session cookies:

```bash
curl -s -c /tmp/synaptiverse.cookies -X POST http://127.0.0.1:8000/api/v1/auth/patient/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+2348012345678","password":"Password123!"}'
```

List tickets using the authenticated tenant session:

```bash
curl -s -b /tmp/synaptiverse.cookies http://127.0.0.1:8000/api/v1/tickets
```

Escalate a ticket:

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/tickets/<ticket-id>/escalate \
  -b /tmp/synaptiverse.cookies
```

## 4. Run the backend tests

```bash
cd backend
PYTHONPATH=$PWD /usr/local/bin/python3 -m pytest -q tests/test_audit_service.py
```

## 5. Validate the frontend build

```bash
cd frontend
npm run build
```

## Notes for local testing

- The backend uses a local SQLite file at backend/synaptiverse.db.
- The default tenant ID is 11111111-1111-1111-1111-111111111111.
- If you hit a database schema error, remove the local SQLite file and restart the backend:

```bash
cd backend
rm -f synaptiverse.db
```

## Main routes to try

- Booking page: /book
- Clinic queue: /clinic/queue
- Patient queue: /dashboard/queue
- Appointment slots: /appointments
- Backend health: /health

## Project structure

```text
backend/
  app/                 FastAPI app, routes, models, schemas
frontend/
  src/app/             Next.js pages and routes
  src/components/       UI components for queues, booking, and shell layouts
  src/lib/             API clients and shared types
```
