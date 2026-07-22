export type SynaptiverseRole =
  | 'patient'
  | 'caregiver'
  | 'clinician'
  | 'facility'
  | 'diagnostic_service'
  | 'pharmacy'
  | 'emergency_transport'
  | 'payer'
  | 'network_admin'
  | 'synaptiverse_admin';

export type TextDirection = 'ltr' | 'rtl';

export type RegionPolicyProfile = {
  regionId: string;
  countryCode: string;
  displayName: string;
  defaultLanguage: string;
  supportedLanguages: string[];
  textDirection: TextDirection;
  timeZones: string[];
  currencyCode: string;
  measurementSystem: 'metric' | 'imperial' | 'mixed';
  emergencyGuidanceSource: 'verified_regional_configuration';
  emergencyContactConfigured: boolean;
  sensitiveDataResidency: 'region_scoped' | 'country_scoped';
  crossBorderTransferRequiresApproval: boolean;
  clinicianJurisdictionRequired: boolean;
};

export type RoutingFactor =
  | 'clinical_capability'
  | 'urgency'
  | 'travel_time'
  | 'capacity'
  | 'operating_status'
  | 'specialist_availability'
  | 'payer_coverage'
  | 'jurisdiction';

export type ServiceBoundary = {
  service: string;
  frontendResponsibility: string;
  backendResponsibility: string;
};

export const globalClinicalBoundary = {
  positioning: 'Right care. Right facility. Right time.',
  patientFacingDisclaimer:
    'SynaptiVerse supports care coordination and does not diagnose, replace a clinician, or replace emergency services.',
  safetyRules: [
    'Never hardcode emergency numbers in product UI.',
    'Do not encode personal or health information in QR codes.',
    'Render triage output as explainable recommendations requiring clinical validation.',
    'Keep identifiable patient and clinical data scoped by tenant, region, and residency policy.',
    'Treat cross-border care access as an explicit consented and audited workflow.',
  ],
} as const;

export const demoRegionPolicyProfiles: RegionPolicyProfile[] = [
  {
    regionId: 'demo-global',
    countryCode: 'XX',
    displayName: 'Global Demo Region',
    defaultLanguage: 'en',
    supportedLanguages: ['en', 'qps-demo'],
    textDirection: 'ltr',
    timeZones: ['UTC'],
    currencyCode: 'USD',
    measurementSystem: 'metric',
    emergencyGuidanceSource: 'verified_regional_configuration',
    emergencyContactConfigured: false,
    sensitiveDataResidency: 'region_scoped',
    crossBorderTransferRequiresApproval: true,
    clinicianJurisdictionRequired: true,
  },
];

export const routingFactors: RoutingFactor[] = [
  'clinical_capability',
  'urgency',
  'travel_time',
  'capacity',
  'operating_status',
  'specialist_availability',
  'payer_coverage',
  'jurisdiction',
];

export const serviceBoundaries: ServiceBoundary[] = [
  {
    service: 'identity_and_auth',
    frontendResponsibility: 'Render role-aware sessions, redirects, and secure logout flows.',
    backendResponsibility: 'Own credentials, JWT/session refresh, MFA, tenant context, and role authorization.',
  },
  {
    service: 'triage_and_routing',
    frontendResponsibility: 'Collect guided intake, display explainable routing recommendations, and show loading/error states.',
    backendResponsibility: 'Own rules, jurisdiction policy, routing scores, appointment creation, and audit events.',
  },
  {
    service: 'regional_configuration',
    frontendResponsibility: 'Render locale-aware terminology, formatting, and emergency guidance from configuration.',
    backendResponsibility: 'Validate and store verified region policy profiles and regional data residency rules.',
  },
  {
    service: 'care_collaboration',
    frontendResponsibility: 'Show referrals, specialist exchange, records release, and notification states from APIs.',
    backendResponsibility: 'Own permissions, consent, cross-organization handoffs, records exchange, and websocket delivery.',
  },
  {
    service: 'payments_and_payers',
    frontendResponsibility: 'Display plan, authorization, and payment statuses returned by APIs.',
    backendResponsibility: 'Own payment adapters, payer verification, claims workflows, webhooks, and reconciliation.',
  },
];

export const roleWorkspaceRoutes: Record<SynaptiverseRole, string> = {
  patient: '/dashboard',
  caregiver: '/dashboard',
  clinician: '/specialist/dashboard',
  facility: '/hospital/dashboard',
  diagnostic_service: '/lab/dashboard',
  pharmacy: '/pharmacy/dashboard',
  emergency_transport: '/moh/dashboard',
  payer: '/hmo/dashboard',
  network_admin: '/moh/dashboard',
  synaptiverse_admin: '/dashboard/admin',
};
