# Offline Queue Synchronization — 2026-07-16

## Client behaviour

- Nurse escalation and status actions update local cards immediately.
- Offline actions persist in `localStorage` with a stable UUID and the ticket version observed by the nurse.
- Repeated pending actions of the same type for one ticket replace the older pending action instead of accumulating duplicates.
- Pending cards display reduced opacity and a `Pending Sync` badge.
- Reconnect replays pending actions and then reloads the authoritative tenant queue.

## Server behaviour

- `tickets.version` increments for every staff mutation.
- Clients send `expected_version`; stale versions receive `409 Conflict` plus the current ticket representation.
- `x-idempotency-key` receipts persist in `client_mutations` under tenant RLS.
- Replaying the same key/action/resource returns the original response without applying the mutation twice.
- Reusing a key for another resource or action returns `409 Conflict`.
- Ticket and appointment changes broadcast only to the authenticated tenant WebSocket room.

## Conflict policy

Clinical server state wins when an offline mutation conflicts with a newer server version. The stale action is discarded and the client reloads the queue. Non-conflict transport failures remain queued for the next reconnect.

