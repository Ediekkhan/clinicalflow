# [PROJECT_NAME] Healthtech Triage MVP

Production-oriented MVP scaffold for a Nigerian B2B multi-tenant clinic triage and appointment scheduling platform. It includes a FastAPI backend, PostgreSQL tenant isolation with RLS, Neo4j deterministic clinical routing, Redis cached local lexicons, channel webhook stubs, and a Next.js App Router frontend with all 11 requested viewports.

## Structure

- `backend/` - FastAPI app, SQLAlchemy models, RLS-aware services, WebSockets, channel stubs.
- `backend/migrations/001_init.sql` - PostgreSQL schema, constraints, indexes, and RLS policies.
- `backend/scripts/neo4j_seed.cypher` - Read-only clinical ontology seed.
- `backend/scripts/seed_demo.py` - Demo Uyo tenant, staff PINs, and provider slots.
- `frontend/` - Next.js App Router, Tailwind tokens, realtime queue dashboard, appointment grid, public/patient screens.
- `docker-compose.yml` - PostgreSQL, Redis, and Neo4j for local development.

## Local Services

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis neo4j
```

Load the Neo4j seed through the Neo4j browser at `http://localhost:7474` or run the Cypher file with your preferred Neo4j client.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python scripts/seed_demo.py
uvicorn app.main:app --reload --port 8000
```

Important routes:

- `GET /api/v1/health`
- `GET /api/v1/tickets`
- `POST /api/v1/tickets`
- `PATCH /api/v1/tickets/{id}/escalate`
- `GET /api/v1/appointments/slots`
- `POST /api/v1/webhooks/whatsapp`
- `POST /api/v1/webhooks/sms`
- `WS /api/v1/ws/triage`

Tenant context is accepted from a bearer token or `X-Tenant-Id`. The demo tenant is `00000000-0000-4000-8000-000000000001`.

Demo PINs after seeding:

- Nurse: `1234`
- Admin: `4321`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Routes:

- `/` - public marketing site and CMD ROI calculator.
- `/book` - patient self-service booking.
- `/my-visit` - live digital ticket view with shared-phone switching.
- `/channels/whatsapp` - WhatsApp template canvas.
- `/channels/sms` - SMS text template canvas.
- `/auth/login` - role and PIN authentication gateway.
- `/dashboard/queue` - realtime nurse triage Kanban with forced overtake.
- `/dashboard/appointments` - provider calendar grid with drag/drop and lockout controls.
- `/dashboard/admin/settings` - tenant channel and staff control panel.
- `/dashboard/waiting-room` - high-contrast TV display with native speech synthesis.

## RLS Model

The backend sets the transaction-local PostgreSQL variable using `set_config('app.current_tenant_id', tenant_id, true)`, equivalent to `SET LOCAL`, before business queries run. Policies compare each row’s `tenant_id` against `current_setting('app.current_tenant_id', true)::uuid`.

## Realtime And Offline Behavior

The nurse dashboard opens `/api/v1/ws/triage` for all realtime queue updates. Local actions update the UI immediately. During network loss, actions are stored in `localStorage`, affected cards show reduced opacity with `⏱️ Pending Sync`, and the sticky toast switches between connected, reconnecting, and offline states.

# clinicalflow
# clinicalflow
# clinicalflow
