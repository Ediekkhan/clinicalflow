# Baseline Validation — 2026-07-16

## Verified environment

- Python: 3.13.4 (the application requirement remains Python 3.11+)
- FastAPI: 0.139.0
- Starlette: 1.3.1
- Next.js: 16.2.7

## Results

| Check | Command | Result |
| --- | --- | --- |
| Backend tests | `cd backend && PYTHONPATH=$PWD /usr/local/bin/python3 -m pytest -q` | Pass: 58 tests, including critical workflows, notifications, operational controls, production safety, retention, metrics, WebSockets, offline behavior, and isolation |
| Browser critical paths | `cd frontend && npm run test:e2e` | Pass: 4 Chromium flows using an isolated temporary database and fresh servers, covering all login surfaces, booking confirmation, forced overtake, and scheduler locking |
| Frontend typecheck | `cd frontend && npm run typecheck` | Pass |
| Frontend production build | `cd frontend && npm run build` | Pass: 109 static routes plus middleware |

The production build requires network access on a clean machine because the root layout uses `next/font` with Google-hosted DM Sans and DM Serif Display. The first sandboxed build failed only while fetching those fonts; the network-enabled build compiled and prerendered successfully.

## Known non-blocking warning

SQLAlchemy reports that model defaults using `datetime.utcnow()` are deprecated under Python 3.13. Replace them with timezone-aware UTC values while implementing the database migration foundation.

## Dependency correction

The repository previously had no Python dependency manifest, and Starlette's test client could not be imported because `httpx2` was absent. `backend/requirements.txt` now declares the runtime database/API dependencies and test dependencies needed to reproduce this baseline.
