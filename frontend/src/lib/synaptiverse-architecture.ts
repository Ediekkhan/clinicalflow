export type SynaptiverseRole =
  | 'patient'
  | 'doctor'
  | 'facility'
  | 'hmo'
  | 'pharmacy'
  | 'laboratory'
  | 'nurse'
  | 'government_admin';

export type SynaptiverseRouteAlias = {
  source: string;
  currentUiTarget: string;
  owner: SynaptiverseRole;
  intent: string;
};

export const synaptiversePositioning = {
  productName: 'SynaptiVerse',
  promise: 'Right care. Right facility. Right time.',
  frontendBoundary:
    'The frontend renders authenticated API data, empty states, loading states, and websocket updates. It does not own clinical decisions or backend authorization.',
  clinicalSafetyBoundary: [
    'AI triage output is advisory and must route to licensed care workflows.',
    'Escalation messaging should direct users toward care without replacing emergency or clinician judgement.',
    'Editable-once clinical identity fields are enforced by backend locked_fields and reflected by the UI.',
  ],
} as const;

export const synaptiverseRoleMatrix = [
  {
    role: 'patient',
    dashboard: '/dashboard',
    primaryWorkflows: ['triage', 'queue tracking', 'appointments', 'health card', 'history'],
  },
  {
    role: 'doctor',
    dashboard: '/specialist/dashboard',
    primaryWorkflows: ['patient queue', 'consultations', 'orders', 'prescriptions', 'schedule'],
  },
  {
    role: 'facility',
    dashboard: '/hospital/dashboard',
    primaryWorkflows: ['queue operations', 'departments', 'specialists', 'appointments', 'analytics'],
  },
  {
    role: 'hmo',
    dashboard: '/hmo/dashboard',
    primaryWorkflows: ['member verification', 'authorizations', 'claims', 'network monitoring'],
  },
  {
    role: 'pharmacy',
    dashboard: '/pharmacy/dashboard',
    primaryWorkflows: ['prescription intake', 'fulfilment', 'inventory', 'delivery'],
  },
  {
    role: 'laboratory',
    dashboard: '/lab/dashboard',
    primaryWorkflows: ['test requests', 'sample collection', 'results release'],
  },
  {
    role: 'nurse',
    dashboard: '/nurse/dashboard',
    primaryWorkflows: ['triage queue', 'vitals', 'home visits', 'care plans'],
  },
  {
    role: 'government_admin',
    dashboard: '/dashboard/admin',
    primaryWorkflows: ['facility oversight', 'verification', 'routing monitor', 'audit reports'],
  },
] as const;

export const synaptiverseServiceBoundaries = [
  {
    service: 'authentication',
    frontendContract: 'Store and clear the session, redirect unauthenticated users, and call auth endpoints when available.',
  },
  {
    service: 'clinical_routing',
    frontendContract: 'Render queue, appointment, referral, and transfer states from API responses and websocket events.',
  },
  {
    service: 'notifications',
    frontendContract: 'Route notification taps only to existing screens and mark notifications as read optimistically.',
  },
  {
    service: 'health_card',
    frontendContract: 'Display current user card fields and respect backend locked_fields for editable-once details.',
  },
  {
    service: 'payments',
    frontendContract: 'Show payment state from the API and hand off gateway initiation to backend-provided URLs.',
  },
] as const;

export const synaptiverseStatusModels = {
  appointment: ['BOOKED', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'NO_SHOW'],
  queueTicket: ['QUEUED', 'BEING_SEEN', 'RESOLVED', 'CANCELLED'],
  prescription: ['PENDING', 'IN_PROGRESS', 'READY', 'FULFILLED', 'CANCELLED'],
  labRequest: ['PENDING', 'COLLECTED', 'PROCESSING', 'RELEASED', 'CANCELLED'],
  authorization: ['REQUESTED', 'APPROVED', 'DENIED', 'EXPIRED'],
} as const;

export const synaptiverseRouteAliases: SynaptiverseRouteAlias[] = [
  { source: '/patient/dashboard', currentUiTarget: '/dashboard', owner: 'patient', intent: 'patient home' },
  { source: '/patient/triage', currentUiTarget: '/dashboard/chat', owner: 'patient', intent: 'AI triage' },
  { source: '/patient/routing', currentUiTarget: '/dashboard/queue', owner: 'patient', intent: 'care routing' },
  { source: '/doctor/dashboard', currentUiTarget: '/specialist/dashboard', owner: 'doctor', intent: 'doctor home' },
  { source: '/doctor/requests', currentUiTarget: '/specialist/patients', owner: 'doctor', intent: 'patient requests' },
  { source: '/facility/dashboard', currentUiTarget: '/hospital/dashboard', owner: 'facility', intent: 'facility home' },
  { source: '/facility/referrals', currentUiTarget: '/hospital/queue', owner: 'facility', intent: 'facility referrals' },
  { source: '/hmo/verification', currentUiTarget: '/hmo/authorizations', owner: 'hmo', intent: 'member verification' },
  { source: '/admin/dashboard', currentUiTarget: '/dashboard/admin', owner: 'government_admin', intent: 'admin home' },
  { source: '/admin/routing-monitor', currentUiTarget: '/dashboard/admin/reports', owner: 'government_admin', intent: 'routing oversight' },
] as const;

export const synaptiverseRealtimeEvents = [
  'TRIAGE_BOOKING_CREATED',
  'QUEUE_STATUS_CHANGED',
  'APPOINTMENT_COMPLETED',
  'PRESCRIPTION_ISSUED',
  'LAB_ORDER_CREATED',
  'LAB_RESULT_RELEASED',
  'VITALS_FLAGGED',
  'AUTHORIZATION_UPDATED',
  'APPOINTMENT_CANCELLED',
  'HOME_VISIT_COMPLETED',
] as const;

export const synaptiverseProductionReadinessChecklist = [
  'All dashboards render API data, skeletons, and empty states.',
  'No dashboard route relies on static patient, facility, claim, or clinical records.',
  'Notification taps route to existing screens and never use undefined path segments.',
  'Realtime events update the matching visible list or trigger a targeted refetch.',
  'Frontend-only demo sessions are clearly local and can be removed when backend auth ships.',
  'Backend-owned services remain behind API contracts instead of being simulated in production UI.',
] as const;
