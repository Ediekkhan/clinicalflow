import type { ProviderSlot, Ticket } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const headers = init.body ? { 'Content-Type': 'application/json', ...init.headers } : init.headers;
  const response = await fetch(`${API_BASE}${url}`, {
    ...init,
    headers,
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('SynaptiVerse API request failed.');
  return response.json();
}

export async function listTickets(): Promise<Ticket[]> {
  return requestJson('/api/v1/tickets');
}

export async function escalateTicket(ticketId: string): Promise<Ticket> {
  return requestJson(`/api/v1/tickets/${ticketId}/escalate`, { method: 'PATCH' });
}

export async function updateTicket(ticketId: string, payload: Partial<Ticket>): Promise<Ticket> {
  return requestJson(`/api/v1/tickets/${ticketId}`, { method: 'PATCH', body: JSON.stringify(payload) });
}

export async function createTicket(payload: {
  customer_phone: string;
  raw_intake_text: string;
  appointment_slot?: string | null;
  channel?: 'WEB';
}) {
  return requestJson('/api/v1/tickets', { method: 'POST', body: JSON.stringify({ channel: 'WEB', ...payload }) });
}

export async function listOpenSlots(): Promise<ProviderSlot[]> {
  return requestJson('/api/v1/appointments/slots');
}

export async function lockSlot(slotId: string, isLocked: boolean, reason?: string) {
  return requestJson(`/api/v1/appointments/slots/${slotId}/lock`, { method: 'PATCH', body: JSON.stringify({ is_locked: isLocked, reason }) });
}

