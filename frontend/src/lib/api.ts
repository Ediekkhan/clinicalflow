import { demoTenantId, type ProviderSlot, type Ticket } from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

const tenantHeaders = {
  'Content-Type': 'application/json',
  'X-Tenant-Id': demoTenantId,
};

export async function listTickets(): Promise<Ticket[]> {
  const response = await fetch(`${API_BASE}/api/v1/tickets`, {
    headers: tenantHeaders,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error('Unable to load queue tickets.');
  }
  return response.json();
}

export async function escalateTicket(ticketId: string): Promise<Ticket> {
  const response = await fetch(`${API_BASE}/api/v1/tickets/${ticketId}/escalate`, {
    method: 'PATCH',
    headers: tenantHeaders,
  });
  if (!response.ok) {
    throw new Error('Unable to force overtake ticket.');
  }
  return response.json();
}

export async function updateTicket(ticketId: string, payload: Partial<Ticket>): Promise<Ticket> {
  const response = await fetch(`${API_BASE}/api/v1/tickets/${ticketId}`, {
    method: 'PATCH',
    headers: tenantHeaders,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('Unable to update ticket.');
  }
  return response.json();
}

export async function createTicket(payload: {
  customer_phone: string;
  raw_intake_text: string;
  appointment_slot?: string | null;
  channel?: 'WEB';
}) {
  const response = await fetch(`${API_BASE}/api/v1/tickets`, {
    method: 'POST',
    headers: tenantHeaders,
    body: JSON.stringify({ channel: 'WEB', ...payload }),
  });
  if (!response.ok) {
    throw new Error('Unable to create ticket.');
  }
  return response.json();
}

export async function listOpenSlots(): Promise<ProviderSlot[]> {
  const response = await fetch(`${API_BASE}/api/v1/appointments/slots`, {
    headers: tenantHeaders,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error('Unable to load provider slots.');
  }
  return response.json();
}

export async function lockSlot(slotId: string, isLocked: boolean, reason?: string) {
  const response = await fetch(`${API_BASE}/api/v1/appointments/slots/${slotId}/lock`, {
    method: 'PATCH',
    headers: tenantHeaders,
    body: JSON.stringify({ is_locked: isLocked, reason }),
  });
  if (!response.ok) {
    throw new Error('Unable to update slot lock.');
  }
  return response.json();
}

