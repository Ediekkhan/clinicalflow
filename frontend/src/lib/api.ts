import type { Appointment, HospitalDepartment, HospitalPatient, HospitalSpecialist, ProviderSlot, Ticket } from '@/lib/types';

export type ListResponse<T> = {
  items?: T[];
  results?: T[];
  data?: T[];
};

export function normalizeList<T>(response: unknown): T[] {
  if (Array.isArray(response)) return response;
  if (response && typeof response === 'object') {
    const value = response as ListResponse<T>;
    if (Array.isArray(value.items)) return value.items;
    if (Array.isArray(value.results)) return value.results;
    if (Array.isArray(value.data)) return value.data;
  }
  return [];
}

const CONFIGURED_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? (process.env.NODE_ENV === 'production' ? '/healthcare-api' : 'http://localhost:8000');
let refreshPromise: Promise<boolean> | null = null;
let redirectingToLogin = false;

function getApiBase() {
  if (typeof window === 'undefined') return CONFIGURED_API_BASE;
  try {
    const configured = new URL(CONFIGURED_API_BASE);
    if (configured.hostname === 'localhost' && window.location.hostname === '127.0.0.1') {
      configured.hostname = '127.0.0.1';
      return configured.toString().replace(/\/$/, '');
    }
    if (configured.hostname === '127.0.0.1' && window.location.hostname === 'localhost') {
      configured.hostname = 'localhost';
      return configured.toString().replace(/\/$/, '');
    }
  } catch {
    return CONFIGURED_API_BASE;
  }
  return CONFIGURED_API_BASE;
}

function loginDestination() {
  if (typeof window === 'undefined') return '/login';
  const path = window.location.pathname;
  if (path.startsWith('/hospital')) return '/hospital/login';
  if (path.startsWith('/specialist')) return '/specialist/login';
  if (path.startsWith('/nurse')) return '/auth/login';
  if (path.startsWith('/clinic')) return '/auth/login';
  if (path.startsWith('/hmo')) return '/auth/login';
  if (path.startsWith('/lab')) return '/auth/login';
  if (path.startsWith('/pharmacy')) return '/auth/login';
  if (path.startsWith('/moh')) return '/auth/login';
  if (path.startsWith('/dashboard')) return '/login';
  return '/login';
}

function clearRoleCookie() {
  if (typeof document === 'undefined') return;
  document.cookie = 'clinicalflow_role=; Max-Age=0; Path=/; SameSite=Lax';
}

function redirectToLogin(reason = 'session-expired') {
  if (typeof window === 'undefined' || redirectingToLogin) return;
  redirectingToLogin = true;
  clearRoleCookie();
  const next = `${window.location.pathname}${window.location.search}`;
  const params = new URLSearchParams({ next, reason });
  window.location.assign(`${loginDestination()}?${params.toString()}`);
}
export class ApiError extends Error {
  constructor(public status: number, message: string, public detail?: unknown) {
    super(message);
  }
}

async function refreshSessionOnce() {
  if (!refreshPromise) {
    refreshPromise = fetch(`${getApiBase()}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      cache: 'no-store',
    })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}
export async function requestJson<T>(url: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = {
    ...(init.body ? { 'Content-Type': 'application/json' } : {}),
    ...(init.headers ?? {}),
  } as HeadersInit;
  const isAuthRequest = url.startsWith('/api/v1/auth/');
  const response = await fetch(`${getApiBase()}${url}`, {
    ...init,
    headers,
    credentials: 'include',
    cache: 'no-store',
  });

  if (response.status === 401 && retry && !isAuthRequest) {
    const refreshed = await refreshSessionOnce();
    if (refreshed) return requestJson<T>(url, init, false);
    redirectToLogin('session-expired');
    throw new ApiError(401, 'Authentication required');
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = typeof detail === 'string' ? detail : detail?.message ?? payload.message ?? 'ClinicalFlow API request failed.';
    throw new ApiError(response.status, message, detail);
  }

  if (response.status === 204) return null as T;
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

export async function listHospitalSlots(): Promise<ProviderSlot[]> {
  const response = await requestJson<ProviderSlot[] | ListResponse<ProviderSlot>>('/api/v1/hospital/appointment-slots');
  return normalizeList<ProviderSlot>(response);
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

export async function listHospitalAppointments(): Promise<Appointment[]> {
  const response = await requestJson<Appointment[] | ListResponse<Appointment>>('/api/v1/hospital/appointments');
  return normalizeList<Appointment>(response);
}

export async function listHospitalPatients(): Promise<{ identity?: Record<string, unknown>; items: HospitalPatient[] }> {
  return requestJson('/api/v1/hospital/patients');
}

export async function listHospitalSpecialists(): Promise<{ identity?: Record<string, unknown>; items: HospitalSpecialist[] }> {
  return requestJson('/api/v1/hospital/specialists');
}

export async function listHospitalDepartments(): Promise<{ identity?: Record<string, unknown>; items: HospitalDepartment[] }> {
  return requestJson('/api/v1/hospital/departments');
}

export async function rescheduleAppointment(appointmentId: string, slotId: string): Promise<Appointment> {
  return requestJson(`/api/v1/appointments/${appointmentId}/reschedule`, { method: 'PATCH', body: JSON.stringify({ slot_id: slotId }) });
}

export async function decideHospitalTicket(ticketId: string, decision: 'ACCEPT' | 'REJECT' | 'REDIRECT', reason?: string, redirectFacilityId?: string) {
  return requestJson(`/api/v1/hospital/tickets/${ticketId}/facility-decision`, { method: 'POST', body: JSON.stringify({ decision, reason, redirect_facility_id: redirectFacilityId }) });
}

export async function transitionHospitalTicket(ticketId: string, status: string, reason?: string) {
  return requestJson(`/api/v1/hospital/tickets/${ticketId}/transition`, { method: 'POST', body: JSON.stringify({ status, reason }) });
}

export async function listAssignmentRequests() {
  return requestJson<Array<Record<string, unknown>>>('/api/v1/appointments/assignment-requests');
}

export async function acceptAppointment(appointmentId: string) {
  return requestJson<Appointment>(`/api/v1/appointments/${appointmentId}/accept`, { method: 'POST', body: JSON.stringify({}) });
}

export async function startAppointmentEncounter(appointmentId: string) {
  return requestJson<Record<string, unknown>>(`/api/v1/appointments/${appointmentId}/encounter`, { method: 'POST', body: JSON.stringify({}) });
}

export async function addEncounterNote(encounterId: string, body: string, noteType = 'PROGRESS') {
  return requestJson<Record<string, unknown>>(`/api/v1/encounters/${encounterId}/notes`, { method: 'POST', body: JSON.stringify({ body, note_type: noteType }) });
}
