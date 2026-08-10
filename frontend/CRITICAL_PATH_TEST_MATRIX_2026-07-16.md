# Critical Path Test Matrix

## Browser coverage

Playwright Chromium tests start the real Next.js and FastAPI applications and cover:

- patient credential login and authenticated dashboard navigation;
- specialist credential login and hospital account login;
- public complaint intake, slot selection, persistent booking, and confirmation receipt;
- nurse PIN login, forced critical overtake, and persistent schedule-slot locking.

Run with:

```bash
cd frontend
npm run test:e2e
```

Install the browser once on a new machine with `npx playwright install chromium`.

## Backend integration coverage

The backend suite covers persistent sessions/rotation/logout, role denial, trusted tenant context, PostgreSQL RLS generation, patient record scoping, signed channel webhooks, ticket/queue escalation, appointment booking/reschedule/cancel/block, specialist assignment and notes, administrative intake controls, rate limiting, Neo4j fallback, Redis degradation, idempotent offline replay, optimistic conflicts, and WebSocket authentication/tenant-targeted delivery.

Run with:

```bash
cd backend
PYTHONPATH=$PWD /usr/local/bin/python3 -m pytest -q
```

## Test environment note

The browser web server uses the system Python. If it warns that no WebSocket implementation is installed, install the declared backend requirements; `uvicorn[standard]` supplies the production WebSocket dependency. WebSocket protocol behavior is independently covered by the backend suite.
