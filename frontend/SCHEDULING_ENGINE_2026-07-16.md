# Persistent Scheduling Engine — 2026-07-16

## Data model

- `providers` stores tenant-owned clinicians, specialties, rooms, and active state.
- `provider_slots` stores live availability, emergency locks, reasons, and booking state.
- `appointments` links a ticket and phone-scoped patient workflow to a provider slot.

All three tables have PostgreSQL RLS policies. Migration `20260716_0005` creates the schema and the local seed creates five days of demonstration availability for three providers.

## Consistency rules

- Booking and slot changes acquire row locks with `SELECT ... FOR UPDATE` on PostgreSQL.
- A locked or booked slot returns `409 Conflict`.
- Booking marks the slot booked and copies its time to the ticket in one transaction.
- Cancellation releases the slot and clears the ticket time.
- Rescheduling locks the appointment and both slots, releases the old slot, reserves the new slot, and updates the ticket.
- Booking, cancellation, rescheduling, and slot locks broadcast appointment updates to the tenant WebSocket room.

## Surfaces

- Public `/book` creates the ticket and reserves the selected live slot.
- Patient `/dashboard/appointments` lists persistent appointments and supports cancellation.
- Staff `/clinic/appointments` and `/hospital/appointments` render the persistent provider grid, emergency blocks, and drag/drop rescheduling.
- WhatsApp/SMS intake can list slots, confirm a slot, and cancel the phone's active appointment.

Provider delivery adapters and external SMS/WhatsApp signatures remain T17 work.

