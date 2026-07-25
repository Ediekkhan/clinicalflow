'use client';

import { clearDemoSession, getDemoApiResponse } from '@/lib/demo-session';

const CONFIGURED_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

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

async function refreshSession() {
  return fetch(`${getApiBase()}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });
}

async function request(method: 'GET' | 'POST' | 'PATCH' | 'DELETE', url: string, body?: object, retry = true) {
  const isAuthenticationRequest = url.startsWith('/api/v1/auth/');
  if (!isAuthenticationRequest) {
    const demoResponse = getDemoApiResponse(method, url, body);
    if (demoResponse !== undefined) return demoResponse;
  }

  const response = await fetch(`${getApiBase()}${url}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  });

  if (response.status === 401 && retry) {
    const refreshed = await refreshSession();
    if (!refreshed.ok) {
      if (typeof window !== 'undefined') window.location.href = '/login';
      return null;
    }
    return request(method, url, body, false);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail?.message ?? payload.detail ?? payload.message ?? 'Request failed');
  }

  if (response.status === 204) {
    if (url === '/api/v1/auth/logout' && typeof document !== 'undefined') {
      document.cookie = 'synaptiverse_role=; Max-Age=0; Path=/; SameSite=Lax';
    }
    return null;
  }
  const payload = await response.json();
  if (url.includes('/auth/') && url.endsWith('/login') && typeof document !== 'undefined' && typeof payload?.role === 'string') {
    clearDemoSession();
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `synaptiverse_role=${encodeURIComponent(payload.role)}; Max-Age=1209600; Path=/; SameSite=Lax${secure}`;
  }
  return payload;
}

export const api = {
  post: (url: string, body: object) => request('POST', url, body),
  get: (url: string) => request('GET', url),
  patch: (url: string, body: object) => request('PATCH', url, body),
  delete: (url: string) => request('DELETE', url),
};
