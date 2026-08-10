# Morning Pitch Deployment: Render + Neon

## Recommended MVP topology

- Frontend: keep the current Next.js deployment target (Vercel is suitable).
- Backend and WebSockets: Render Free Web Service using the root `render.yaml`.
- Persistent relational database: Neon Free PostgreSQL.
- Neo4j and Redis: leave disabled for the pitch; the current MVP does not depend on them yet.

This combination is selected because Render supports FastAPI and WebSockets, while Neon Free has no fixed expiry. Render's own free PostgreSQL expires after 30 days.

## 1. Create the Neon database

1. Create a Neon account and Free project.
2. Copy the pooled Postgres connection string.
3. Keep it private; it becomes Render's `DATABASE_URL` secret.

## 2. Deploy the backend on Render

1. Push this repository to a Git provider supported by Render.
2. In Render, choose **New → Blueprint** and select the repository. Render reads `render.yaml`.
3. Choose the Free instance.
4. Supply these secret/environment values when prompted:

```env
DATABASE_URL=postgresql://USER:PASSWORD@NEON_HOST/DB?sslmode=require
CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app,http://127.0.0.1:3000
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none
```

5. Deploy and confirm the startup Alembic migration succeeds before Uvicorn starts.
6. Open `https://YOUR-SERVICE.onrender.com/health` and expect:

```json
{"status":"ok","service":"clinicalflow","dependencies":{"redis":"degraded-local","neo4j":"degraded-fallback"}}
```

## 3. Point the frontend at Render

Set these in the frontend hosting environment:

```env
NEXT_PUBLIC_API_BASE_URL=https://YOUR-SERVICE.onrender.com
NEXT_PUBLIC_WS_BASE_URL=wss://YOUR-SERVICE.onrender.com
```

Redeploy the frontend. Use the same hostname style consistently; authentication uses secure HttpOnly cookies.

## 4. Pitch credentials

| Surface | Credential |
| --- | --- |
| Patient `/login` | `+2348012345678` / `Password123!` |
| Specialist `/specialist/login` | `dr.ada@example.com` / `Password123!` |
| Nurse PIN `/auth/login` | role Nurse / PIN `2468` |
| Admin PIN `/auth/login` | role Admin / PIN `1357` |
| Hospital `/hospital/login` | code `UYO-FAMILY`, any displayed role / `Password123!` |

These are demo credentials only. Change or remove them before any real-world pilot.

## 5. Pre-pitch checklist

Render Free services spin down after 15 minutes without inbound HTTP or WebSocket traffic and may take about a minute to wake. Ten minutes before presenting:

1. Open the backend `/health` URL and wait for `200 OK`.
2. Open the frontend and log in as nurse.
3. Create one test booking.
4. Confirm it appears in the nurse queue.
5. Test forced overtake and the waiting-room screen.
6. Keep the nurse WebSocket screen connected during the pitch.

## Free-tier caveats

- Render Free is for previews, not production healthcare workloads.
- Its filesystem is ephemeral, which is why SQLite must not be used there.
- Render grants 750 free instance-hours per workspace monthly and can suspend services when limits are exhausted.
- Neon Free currently includes 0.5 GB storage and 100 CU-hours monthly per project, with scale-to-zero when idle.
- Do not enter real patient data during the pitch. A compliant clinical pilot requires security, privacy, retention, monitoring, backup, and contractual review.

Sources: [Render free services](https://render.com/docs/free), [Render FastAPI/web service deployment](https://render.com/docs/web-services), [Neon Free plan](https://neon.com/pricing).
