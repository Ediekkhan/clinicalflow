import {
  BookOpen,
  Boxes,
  CloudCog,
  Code2,
  Network,
  Rocket,
  ShieldCheck,
  Workflow,
} from 'lucide-react';

export const docsNavigation = [
  {
    title: 'Start here',
    items: [
      { href: '/developers', label: 'Welcome to ClinicalFlow', description: 'README and local setup', icon: BookOpen },
      { href: '/developers/project-structure', label: 'Project breakdown', description: 'Repository and modules', icon: Boxes },
      { href: '/developers/architecture', label: 'System architecture', description: 'Services and data flow', icon: Network },
    ],
  },
  {
    title: 'Build',
    items: [
      { href: '/developers/api-reference', label: 'API reference', description: 'Routes and authentication', icon: Code2 },
      { href: '/developers/deployment', label: 'Deployments', description: 'Local, staging, production', icon: Rocket },
    ],
  },
];

export const quickLinks = [
  { href: '/developers/api-reference', label: 'Explore the API', icon: Code2 },
  { href: '/developers/architecture', label: 'Understand the system', icon: Workflow },
  { href: '/developers/deployment', label: 'Deploy an environment', icon: CloudCog },
  { href: '/developers#security-boundaries', label: 'Review security boundaries', icon: ShieldCheck },
];

export const apiGroups = [
  {
    name: 'Authentication & signup',
    description: 'Sessions, role-aware login, patient onboarding and workspace selection.',
    endpoints: [
      ['POST', '/api/v1/auth/{role}/login', 'Create a role session'],
      ['POST', '/api/v1/auth/refresh', 'Rotate an access session'],
      ['POST', '/api/v1/auth/logout', 'End the current session'],
      ['GET', '/api/v1/auth/{role}/me', 'Read the authenticated account'],
      ['POST', '/api/v1/signup/patient', 'Create a patient application'],
      ['POST', '/api/v1/signup/{entity}', 'Create an organization or professional application'],
      ['POST', '/api/v1/signup/verify-phone', 'Verify a patient phone OTP'],
      ['GET', '/api/v1/staff/workspaces', 'List permitted workspaces'],
    ],
  },
  {
    name: 'Patient care & tickets',
    description: 'Triage, queue coordination, clinical tickets and the patient longitudinal view.',
    endpoints: [
      ['POST', '/api/v1/public/triage-preview', 'Preview a public triage result'],
      ['POST', '/api/v1/patient/triage', 'Create authenticated triage'],
      ['POST', '/api/v1/tickets', 'Open a clinical coordination ticket'],
      ['GET', '/api/v1/tickets', 'List tenant tickets'],
      ['PATCH', '/api/v1/tickets/{ticket_id}', 'Update ticket workflow state'],
      ['GET', '/api/v1/patient/dashboard', 'Read the patient dashboard'],
      ['GET', '/api/v1/patient/health-card', 'Read the portable health card'],
      ['GET', '/api/v1/patient/history', 'Read patient history'],
    ],
  },
  {
    name: 'Hospitals & appointments',
    description: 'Facility queues, departments, staff, routing decisions and scheduling.',
    endpoints: [
      ['GET', '/api/v1/hospital/me', 'Read the active facility workspace'],
      ['GET', '/api/v1/hospital/departments', 'List facility departments'],
      ['GET', '/api/v1/hospital/waiting-room', 'Read the waiting room'],
      ['POST', '/api/v1/hospital/tickets/{ticket_id}/facility-decision', 'Accept or redirect a ticket'],
      ['GET', '/api/v1/appointments/slots', 'List appointment slots'],
      ['POST', '/api/v1/appointments', 'Create an appointment'],
      ['GET', '/api/v1/hospital/appointments', 'List facility appointments'],
      ['POST', '/api/v1/appointments/{appointment_id}/encounter', 'Start an encounter'],
    ],
  },
  {
    name: 'Clinical network',
    description: 'Specialists, referrals, pharmacy, laboratory and insurer workflows.',
    endpoints: [
      ['POST', '/api/v1/referrals', 'Create a referral'],
      ['GET', '/api/v1/referrals', 'List referrals'],
      ['POST', '/api/v1/laboratory/orders', 'Create a laboratory order'],
      ['POST', '/api/v1/laboratory/orders/{order_id}/results', 'Record laboratory results'],
      ['POST', '/api/v1/prescriptions', 'Create a prescription'],
      ['POST', '/api/v1/pharmacy/orders/{order_id}/dispense', 'Record dispensing'],
      ['POST', '/api/v1/coverage/eligibility', 'Check coverage eligibility'],
      ['POST', '/api/v1/claims', 'Submit an insurance claim'],
    ],
  },
  {
    name: 'Channels & platform',
    description: 'WhatsApp/SMS intake, documents, terminology, billing and platform controls.',
    endpoints: [
      ['POST', '/api/v1/channels/{channel}/intake', 'Process channel intake'],
      ['GET', '/api/v1/webhooks/whatsapp', 'Verify a WhatsApp webhook'],
      ['POST', '/api/v1/webhooks/{channel}', 'Receive a channel event'],
      ['POST', '/api/v1/documents/upload-url', 'Create a private upload URL'],
      ['GET', '/api/v1/public/terminology/concepts', 'Search published concepts'],
      ['POST', '/api/v1/billing/checkout', 'Create a checkout'],
      ['GET', '/api/v1/platform/signup-applications', 'Review signup applications'],
      ['GET', '/api/v1/platform/facility-verifications', 'List facility verification cases'],
    ],
  },
] as const;

export const repositoryTree = `clinicalflow/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy domain models
│   │   ├── routes/          # FastAPI route modules by domain
│   │   ├── services/        # Auth, routing, providers and workers
│   │   ├── config.py        # Validated runtime configuration
│   │   └── main.py          # Application lifecycle and middleware
│   ├── migrations/          # Alembic database history
│   └── tests/               # API and workflow tests
├── frontend/
│   ├── src/app/             # Next.js routes
│   ├── src/components/      # Shared UI and portal modules
│   ├── src/lib/             # API, auth and configuration clients
│   └── tests/e2e/           # Playwright critical paths
├── docs/                    # Engineering and operations runbooks
├── scripts/                 # Operational helpers
├── render.yaml              # Backend service definition
└── README.md                # Repository quick start`;

