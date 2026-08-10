# Implementation test guide

This document covers the MVP features that are currently implemented and the quickest way to verify them locally.

## Implemented features

### Backend
- Health check endpoint
- Ticket creation, listing, escalation, and update
- Triage WebSocket endpoint for queue events
- Basic patient and specialist auth endpoints
- Audit logging for ticket events

### Frontend
- Patient and specialist login pages call the backend
- Queue pages display real ticket data from the backend
- Booking and triage-related UI is wired to the API layer
- Production build succeeds

## Automated checks

Run the backend regression tests:

```bash
cd backend
pytest -q tests/test_auth_routes.py tests/test_audit_service.py
```

Expected result:
- 3 tests passed

Run the frontend build:

```bash
cd frontend
npm run build
```

Expected result:
- Next.js production build completes successfully

## Manual smoke tests

### 1. Backend health
- Open: http://127.0.0.1:8000/health
- Expected: JSON response with `status: ok`

### 2. Create a ticket
- POST to `/api/v1/tickets`
- Body example:

```json
{
  "customer_phone": "+2348012345678",
  "raw_intake_text": "Mild fever and headache",
  "channel": "WEB"
}
```

Expected:
- Status `201`
- Response includes a generated ticket number and tenant ID

### 3. List tickets
- GET `/api/v1/tickets`
- Expected: array of ticket records for the tenant

### 4. Patient login
- POST `/api/v1/auth/patient/login`
- Body:

```json
{
  "phone": "+2348012345678",
  "password": "Password123!"
}
```

Expected:
- Status `200`
- Response includes the patient profile payload

### 5. Specialist login
- POST `/api/v1/auth/specialist/login`
- Body:

```json
{
  "email": "dr.ada@example.com",
  "password": "Password123!"
}
```

Expected:
- Status `200`
- Response includes the specialist profile payload

### 6. Frontend login flow
- Start the frontend and open `/login` or `/specialist/login`
- Enter the demo credentials above
- Expected: the app routes to the corresponding dashboard screen

## Current gaps

These areas are not yet fully implemented and should be treated as follow-up work:
- Full JWT or session-based authentication persistence
- Role-based access control per portal
- Real multi-tenant user management
- End-to-end appointment scheduling beyond the initial slot MVP
