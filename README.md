# SynaptiVerse

Frontend-only demo build for a multi-portal healthcare coordination platform.

This repository currently contains the SynaptiVerse Next.js frontend only. The backend has been removed from this codebase, so the app is set up for demo use without a live API. Demo sessions are stored locally in the browser and every dashboard renders from generic API-shaped data or empty states until a real backend is connected.

## Current Status

- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS.
- Backend: intentionally removed from this repository.
- Demo mode: enabled from `/signup` for every role.
- Mock records: removed from dashboard displays.
- API calls: routed through the frontend API client with a local demo fallback when demo mode is active.

## Demo Sign-In

Run the app, open `/signup`, and choose any workspace. The role card creates a local demo session and routes directly to that dashboard.

Available demo workspaces:

- Patient: `/dashboard`
- Doctor / Specialist: `/specialist/dashboard`
- Hospital / Clinic: `/hospital/dashboard`
- Clinic: `/clinic/dashboard`
- Pharmacy: `/pharmacy/dashboard`
- Laboratory: `/lab/dashboard`
- Nurse: `/nurse/dashboard`
- HMO / Insurance: `/hmo/dashboard`
- Government: `/moh/dashboard`
- Admin: `/dashboard/admin`

Direct role URLs also work, for example:

```text
/signup?type=specialist
/signup?type=pharmacy
/signup?type=admin
```

Admin demo access sets a local role cookie so the protected admin route can be opened during demos.

## Logout

Every dashboard shell includes a logout control. `/logout` clears the local demo session, demo card details, and demo role cookie, then returns to `/signup`.

## Local Development

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000/signup
```

## Validation

Useful checks:

```powershell
cd frontend
npm run typecheck
npm run build
```

The current demo build has been typechecked with:

```powershell
npm run typecheck
```

## API Integration Notes

The backend developer owns API implementations, authentication, persistence, WebSockets, payments, credential verification, audit logging, and deployment infrastructure. The frontend expects the eventual backend to provide endpoints under `/api/v1/...`.

When a real backend is available:

- Keep `NEXT_PUBLIC_API_BASE_URL` or `NEXT_PUBLIC_API_BASE` pointed at the API host.
- Remove or disable the local demo session path when production authentication is ready.
- Keep the loading, empty, and error states in place so dashboards do not show fallback mock records.


## Product Build Specification

The full product and architecture prompt from `synaptiverse_codex_build_prompt.md` has been added at:

```text
docs/synaptiverse-product-build-spec.md
```

It is kept as a reference specification for future backend, routing-engine, security, governance, and end-to-end workflow implementation. The current repository remains a frontend-only demo build.

The spec is also represented in the frontend without changing the existing UI:

- `frontend/src/lib/synaptiverse-architecture.ts` stores role workflows, service boundaries, route alias metadata, status models, realtime event names, and production readiness checks.
- Additive route aliases were added for spec paths such as `/patient/dashboard`, `/doctor/dashboard`, `/facility/dashboard`, and `/admin/dashboard`.
- Alias pages redirect into the existing dashboard UI, so the current layouts stay intact while the project can accept the larger route vocabulary from the build prompt.

## Project Layout

```text
frontend/
  src/app/           App Router pages
  src/components/    Shared UI and dashboard components
  src/hooks/         Frontend hooks
  src/lib/           API client, dashboard config, demo session helpers, types, architecture metadata
```

## Notes For Demo Day

- Use `/signup` as the entry point.
- Tap any role to enter its dashboard.
- Dashboards show generic identities and empty states until the backend provides real data.
- Use Logout to switch roles during a presentation.
