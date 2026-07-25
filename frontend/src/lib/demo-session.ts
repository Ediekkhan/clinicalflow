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

function demoTriageResponse(body?: object) {
  const triageBody = body as { symptom_description?: string; latitude?: number; longitude?: number } | undefined;
  const hasCoordinates = typeof triageBody?.latitude === 'number' && typeof triageBody?.longitude === 'number';
  const symptomText = String(triageBody?.symptom_description ?? '').toLowerCase();
  const critical = symptomText.includes('chest') || symptomText.includes('breath') || symptomText.includes('bleeding');
  const routine = symptomText.includes('rash') || symptomText.includes('itch');
  const urgency = critical ? 'CRITICAL' : routine ? 'ROUTINE' : 'URGENT';
  const severity = critical ? 'SEVERE' : routine ? 'MILD' : 'MODERATE';
  const possibleIllness = critical
    ? 'Possible serious heart or breathing-related emergency'
    : routine
      ? 'Possible skin irritation, allergy, or rash-related illness'
      : 'Possible acute infection or systemic illness';
  return {
    condition_name: critical ? 'Emergency Red Flag' : routine ? 'Dermatological Complaint' : 'Acute Systemic Illness',
    possible_illness: possibleIllness,
    diagnosis_disclaimer: 'This is not a diagnosis. A qualified clinician must confirm what illness you have.',
    urgency,
    specialty: critical ? 'Emergency Medicine' : routine ? 'Dermatology' : 'General Medicine',
    severity,
    severity_label: severity.charAt(0) + severity.slice(1).toLowerCase(),
    severity_message: critical ? 'Severe presentation. Seek emergency care immediately.' : routine ? 'Mild presentation. Book routine care unless symptoms worsen.' : 'Moderate presentation. A clinician should review this today.',
    messages: ['I identified the symptom pattern from your description.', 'Routing source: frontend demo mode.'],
    nearest_clinic: hasCoordinates ? { clinic_name: 'Registered demo hospital', address: 'Coordinate-based demo route', distance_km: 1.2, specialist_name: '', match_basis: 'Nearest active registered hospital by patient coordinates' } : undefined,
    appointment_slot: null,
    ticket: hasCoordinates ? { id: `demo-ticket-${Date.now()}`, ticket_number: 'Demo ticket' } : undefined,
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

  if (method === 'POST' && (url === '/api/v1/patient/triage' || url === '/api/v1/public/triage-preview')) {
    return demoTriageResponse(body);
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
