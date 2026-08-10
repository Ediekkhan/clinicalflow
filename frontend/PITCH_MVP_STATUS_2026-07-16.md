# Pitch MVP Status — 2026-07-16

## Verified complete

- [x] Public landing page with live platform content.
- [x] Interactive ROI calculator with persisted lead capture.
- [x] Functional `/book-demo` capture and confirmation.
- [x] Patient web booking creates a persistent ticket.
- [x] WhatsApp/SMS duplicate-phone family guardrail.
- [x] Nurse PIN authentication and real-time Kanban.
- [x] Forced overtake with audit log and WebSocket broadcast.
- [x] Patient context drawer with raw intake and extracted symptom terms.
- [x] Dedicated `/my-visit` ticket and shared-phone selector.
- [x] Waiting-room feed, large display, and text-to-speech.
- [x] Render + Neon deployment configuration and switching guide.
- [x] Backend regression suite: 27 passing tests.
- [x] Frontend production build: 109 routes prerendered successfully.
- [x] Alembic schema drift check: clean at revision `20260716_0006`.

## Intentionally not checked yet

- [x] Persistent appointment scheduling and provider calendar engine (T09).
- [x] Full offline conflict/idempotency handling (T10).
- [ ] Neo4j clinical graph (T11).
- [ ] Redis shared infrastructure (T12).
- [ ] Complete non-pitch portal APIs and admin controls (remaining T13–T18 scope).
- [ ] Actual Render/Neon deployment and browser smoke test against the public URLs.

No real patient data should be used for this pitch environment.
