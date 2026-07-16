import type { Appointment, ProviderSlot, Ticket } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public status: number, message: string, public detail?: unknown) {
    super(message);
  }
}

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const headers = {
    ...(init.body ? { 'Content-Type': 'application/json' } : {}),
    ...(init.headers ?? {}),
  } as HeadersInit;
  const response = await fetch(`${API_BASE}${url}`, {
    ...init,
    headers,
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = typeof detail === 'string' ? detail : detail?.message ?? 'ClinicalFlow API request failed.';
    throw new ApiError(response.status, message, detail);
  }
  return response.json();
}

export async function listTickets(): Promise<Ticket[]> {
  return requestJson('/api/v1/tickets');
}

export async function escalateTicket(ticketId: string, idempotencyKey?: string, expectedVersion?: number): Promise<Ticket> {
  return requestJson(`/api/v1/tickets/${ticketId}/escalate`, {
    method: 'PATCH',
    headers: {
      ...(idempotencyKey ? { 'x-idempotency-key': idempotencyKey } : {}),
      ...(expectedVersion ? { 'x-expected-version': String(expectedVersion) } : {}),
    },
  });
}

export async function updateTicket(ticketId: string, payload: Partial<Ticket> & { expected_version?: number }, idempotencyKey?: string): Promise<Ticket> {
  return requestJson(`/api/v1/tickets/${ticketId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
    headers: idempotencyKey ? { 'x-idempotency-key': idempotencyKey } : {},
  });
}

export async function createTicket(payload: {
  customer_phone: string;
  raw_intake_text: string;
  appointment_slot?: string | null;
  channel?: 'WEB';
}): Promise<Ticket> {
  return requestJson('/api/v1/tickets', { method: 'POST', body: JSON.stringify({ channel: 'WEB', ...payload }) });
}

export async function listOpenSlots(): Promise<ProviderSlot[]> {
  return requestJson('/api/v1/appointments/slots');
}

export async function lockSlot(slotId: string, isLocked: boolean, reason?: string) {
  return requestJson(`/api/v1/appointments/slots/${slotId}/lock`, { method: 'PATCH', body: JSON.stringify({ is_locked: isLocked, reason }) });
}

export async function bookAppointment(ticketId: string, slotId: string, customerPhone: string): Promise<Appointment> {
  return requestJson('/api/v1/appointments', { method: 'POST', body: JSON.stringify({ ticket_id: ticketId, slot_id: slotId, customer_phone: customerPhone }) });
}

export async function listAppointments(): Promise<Appointment[]> {
  return requestJson('/api/v1/appointments');
}

export async function rescheduleAppointment(appointmentId: string, slotId: string): Promise<Appointment> {
  return requestJson(`/api/v1/appointments/${appointmentId}/reschedule`, { method: 'PATCH', body: JSON.stringify({ slot_id: slotId }) });
}
