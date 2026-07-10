'use client';

export type DemoRole = 'patient' | 'specialist' | 'hospital' | 'clinic' | 'pharmacy' | 'lab' | 'nurse' | 'hmo' | 'moh' | 'admin';

type DemoSession = {
  is_demo: true;
  role: DemoRole;
  created_at: string;
};

type DemoIdentity = {
  name: string;
  subtitle: string;
  badge?: string;
  initials: string;
};

const DEMO_SESSION_KEY = 'synaptiverse_demo_session';
const DEMO_DETAILS_KEY = 'synaptiverse_demo_card_details';
const DEMO_ROLE_COOKIE = 'synaptiverse_role';
const DEMO_COOKIE_MAX_AGE = 60 * 60 * 24;

export const demoDashboardRoutes: Record<DemoRole, string> = {
  patient: '/dashboard',
  specialist: '/specialist/dashboard',
  hospital: '/hospital/dashboard',
  clinic: '/clinic/dashboard',
  pharmacy: '/pharmacy/dashboard',
  lab: '/lab/dashboard',
  nurse: '/nurse/dashboard',
  hmo: '/hmo/dashboard',
  moh: '/moh/dashboard',
  admin: '/dashboard/admin',
};

const demoIdentities: Record<DemoRole, DemoIdentity> = {
  patient: { name: 'Demo User', subtitle: 'Patient portal demo', initials: 'DU' },
  specialist: { name: 'Demo Clinician', subtitle: 'Specialist portal demo', initials: 'DC' },
  hospital: { name: 'Demo Facility', subtitle: 'Hospital portal demo', initials: 'DF' },
  clinic: { name: 'Demo Clinic', subtitle: 'Clinic portal demo', initials: 'DC' },
  pharmacy: { name: 'Demo Pharmacy', subtitle: 'Pharmacy portal demo', initials: 'DP' },
  lab: { name: 'Demo Laboratory', subtitle: 'Laboratory portal demo', initials: 'DL' },
  nurse: { name: 'Demo Nurse', subtitle: 'Nurse portal demo', initials: 'DN' },
  hmo: { name: 'Demo HMO', subtitle: 'Insurance portal demo', initials: 'DH' },
  moh: { name: 'Demo Ministry', subtitle: 'Government portal demo', initials: 'DM' },
  admin: { name: 'Demo Admin', subtitle: 'Administration demo', initials: 'DA' },
};

const demoRoles = new Set<DemoRole>(Object.keys(demoDashboardRoutes) as DemoRole[]);

function readJson<T>(key: string): T | null {
  if (typeof window === 'undefined') return null;
  try {
    const value = window.localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

function writeDemoRoleCookie(role: DemoRole) {
  if (typeof document === 'undefined') return;
  document.cookie = `${DEMO_ROLE_COOKIE}=${encodeURIComponent(role)}; Path=/; SameSite=Lax; Max-Age=${DEMO_COOKIE_MAX_AGE}`;
}

function clearDemoRoleCookie() {
  if (typeof document === 'undefined') return;
  document.cookie = `${DEMO_ROLE_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0`;
}

export function isDemoRole(value: string | null | undefined): value is DemoRole {
  return !!value && demoRoles.has(value as DemoRole);
}

export function startDemoSession(role: DemoRole) {
  const session: DemoSession = { is_demo: true, role, created_at: new Date().toISOString() };
  writeJson(DEMO_SESSION_KEY, session);
  writeDemoRoleCookie(role);
  return session;
}

export function getDemoSession() {
  const session = readJson<DemoSession>(DEMO_SESSION_KEY);
  return session?.is_demo && isDemoRole(session.role) ? session : null;
}

export function clearDemoSession() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(DEMO_SESSION_KEY);
  window.localStorage.removeItem(DEMO_DETAILS_KEY);
  clearDemoRoleCookie();
}

export function getDemoDashboardRoute(role: DemoRole) {
  return demoDashboardRoutes[role];
}

export function getDemoIdentity(role: DemoRole): DemoIdentity {
  return demoIdentities[role];
}

function getDemoCardDetails() {
  return readJson<Record<string, string>>(DEMO_DETAILS_KEY) ?? {};
}

function setDemoCardDetails(details: Record<string, string>) {
  writeJson(DEMO_DETAILS_KEY, details);
}

function genericProfile(role: DemoRole) {
  const identity = getDemoIdentity(role);
  const [firstName = '', ...rest] = identity.name.split(' ');
  return {
    id: 'demo-session',
    is_demo: true,
    role,
    first_name: firstName,
    last_name: rest.join(' '),
    full_name: identity.name,
    name: identity.name,
    specialty: '',
    subtitle: identity.subtitle,
    card_number: '',
    state: '',
    lga: '',
    locked_fields: [],
    ...getDemoCardDetails(),
  };
}

function entityPayload(role: DemoRole) {
  return {
    identity: getDemoIdentity(role),
    stats: [],
    activity: [],
    items: [],
    rows: [],
    notifications: [],
    columns: [],
    chartData: [],
  };
}

export function getDemoApiResponse(method: 'GET' | 'POST' | 'PATCH' | 'DELETE', url: string, body?: object) {
  const session = getDemoSession();
  if (!session) return undefined;

  if (method === 'PATCH' && url === '/api/v1/patient/card-details') {
    const nextDetails = { ...getDemoCardDetails(), ...(body as Record<string, string>) };
    setDemoCardDetails(nextDetails);
    return { ...genericProfile('patient'), ...nextDetails };
  }

  if (method !== 'GET') {
    return { ok: true, is_demo: true };
  }

  if (url === '/api/v1/auth/patient/me') return genericProfile('patient');
  if (url === '/api/v1/auth/specialist/me') return genericProfile(session.role === 'specialist' ? 'specialist' : session.role);
  if (url === '/api/v1/hospital/me') return { ...genericProfile('hospital'), location: '' };
  if (url === '/api/v1/notifications') return [];

  if (url === '/api/v1/patient/dashboard') {
    return { stats: {}, activity: [], health_tip: null };
  }
  if (url === '/api/v1/patient/appointments') return [];
  if (url === '/api/v1/patient/history') return [];
  if (url === '/api/v1/patient/queue') return null;

  const match = url.match(/^\/api\/v1\/(patient|specialist|hospital|clinic|pharmacy|lab|nurse|hmo|moh|admin)\//);
  if (match && isDemoRole(match[1])) {
    return entityPayload(match[1]);
  }

  return entityPayload(session.role);
}
