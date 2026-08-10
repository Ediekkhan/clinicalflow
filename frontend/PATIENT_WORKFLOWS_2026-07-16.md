# Patient Workflows

## Completed surfaces

- `/my-visit` provides a dedicated live ticket, queue position refresh, and shared-phone ticket selector.
- `/book` creates a clinically routed ticket, books a persistent provider slot, and displays a detailed confirmation receipt.
- `/dashboard/appointments` loads the authenticated patient's appointments and supports persistent cancellation with live updates.
- `/dashboard/history` combines patient-scoped triage tickets and appointments into a persistent timeline.
- `/dashboard/settings` updates the authenticated patient's personal and health profile.
- `/dashboard/card` reads and updates persistent health-card details.
- `/dashboard` reports active tickets, live queue position, next appointment, health-card state, and recent activity.

## Authorization and data ownership

All patient dashboard APIs derive tenant and phone scope from the authenticated server-side session. They do not accept a caller-controlled patient or tenant identifier. Profile/card mutations reject non-patient roles. Appointments, tickets, history, and queue data are filtered by the authenticated patient's normalized phone number.

Shared-phone tickets remain distinguishable records linked through `account_group_phone`; the live visit selector never merges their clinical ticket state.

## API contracts

- `GET /api/v1/patient/dashboard`
- `GET /api/v1/patient/queue`
- `GET /api/v1/patient/appointments`
- `GET /api/v1/patient/history`
- `POST /api/v1/patient/triage`
- `PATCH /api/v1/patient/profile`
- `PATCH /api/v1/patient/card-details`
- `PATCH /api/v1/appointments/{id}/cancel`

Patient profile and card fields are stored on `auth_accounts` by Alembic revision `20260716_0007`.
