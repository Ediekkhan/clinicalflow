# Change Summary — 2026-07-16

## Work completed in this session

- Added local frontend environment support:
  - `frontend/.env.local`
  - `frontend/.env.example`
- Updated `.gitignore` to ignore `.env.local` and `.env.*.local`.
- Verified backend auth routes and API connectivity for demo patient and specialist login.
- Confirmed the frontend Next.js production build passes with the new environment configuration.

## Backend status

- Local database is currently SQLite at `backend/synaptiverse.db`.
- Backend config includes a default Neo4j URI, user, and password in `backend/app/config.py`, but there is no active Neo4j integration code in the repository yet.
- Implemented backend endpoints currently include:
  - `/api/v1/auth/{role}/login`
  - `/api/v1/auth/{role}/me`
  - `/api/v1/auth/refresh`
  - `/api/v1/tickets`
  - `/api/v1/tickets/{ticket_id}/escalate`
  - `/api/v1/tickets/{ticket_id}`
  - `/api/v1/appointments/slots`
  - `/api/v1/appointments/slots/{slot_id}/lock`
  - `/api/v1/patient/queue`
  - `/api/v1/patient/triage`
  - `/api/v1/ws/triage`

## Frontend status

- API client layer is wired through `frontend/src/lib/api.ts` and `frontend/src/lib/auth.ts`.
- Local API base is now configured through `NEXT_PUBLIC_API_BASE_URL`.
- Patient login and specialist login pages are wired to backend auth endpoints.
- Many portal pages in `frontend/src/app/` currently render UI shells or EntityDashboard placeholders, but backend support is incomplete for those entity-specific endpoints.

## Key gaps

- Hosted database is not configured; current setup is local SQLite only.
- Neo4j knowledge graph is only present as default config values, not as an implemented schema or integration.
- Portal-specific backend APIs for specialist, hospital, clinic, pharmacy, lab, nurse, HMO, MOH, and admin are largely missing.
- Hospital login page is currently a static code/password form and does not connect to a real authentication backend.

## Notes for follow-up

- Ensure the team can run locally with SQLite while also offering a cloud-hosted database option.
- Build the missing backend endpoints for portal dashboards and entity-specific data.
- Decide whether to implement Neo4j for the medical knowledge graph or remove the placeholder config.
- Add a browser-level smoke test for end-to-end login and portal routing.
