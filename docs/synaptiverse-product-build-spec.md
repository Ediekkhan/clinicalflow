# Codex Build Prompt: SynaptiVerse Healthcare Routing Platform

## Your role

Act as a senior product engineer, UX designer, healthcare-systems architect, security engineer, and QA lead. Build a polished, responsive, production-minded MVP of **SynaptiVerse**, an AI-assisted healthcare triage, routing, appointment, health-card, and cross-hospital collaboration platform for Nigeria.

Do not stop at wireframes or a written plan. Implement the working application, seed it with realistic fictional demo data, run the tests and build, fix failures, and leave the repository in a clean, documented state.

## First actions

1. Inspect the existing repository, its instructions, current stack, routes, components, tests, environment files, and uncommitted changes.
2. Preserve and extend any working implementation. Do not overwrite unrelated work.
3. If a suitable application already exists, follow its conventions and dependencies.
4. If the repository is empty, use this default stack:
   - Next.js with App Router
   - TypeScript with strict mode
   - Tailwind CSS
   - shadcn/ui or an equivalent accessible component system
   - Prisma with PostgreSQL for the intended architecture
   - SQLite as a documented local-development fallback if PostgreSQL is unavailable
   - Auth.js or an equivalent secure authentication abstraction
   - Zod for validation
   - Vitest or Jest for unit and integration tests
   - Playwright for essential end-to-end flows
5. Use adapters for maps, email, SMS, push notifications, payments, HMO verification, video consultation, and hospital EHR integrations. Provide working local mock adapters when real credentials are unavailable.
6. Never hardcode secrets. Add a complete `.env.example`.

## Product vision

SynaptiVerse connects patients, clinics, hospitals, doctors, specialists, and HMOs in one coordinated care-routing network.

The platform should:

- give every registered patient a secure digital and optional physical **SynaptiVerse Health Access Card**;
- collect symptoms through a guided intake experience;
- produce an explainable urgency and specialty recommendation without claiming to diagnose;
- route a patient to the closest **suitable** facility using clinical capability, urgency, travel time, specialist availability, capacity, operating status, and optional HMO coverage;
- create and manage appointments;
- notify the correct doctor based on facility, department, specialty, shift, availability, and capacity;
- let a new hospital create a local patient record linked to the patient's global SynaptiVerse identity;
- allow hospitals to request specialists from other hospitals through remote consultation, visiting-specialist support, or patient transfer;
- return hospital-approved care summaries, results, prescriptions, and follow-up information to the patient;
- give clinics, hospitals, HMOs, doctors, patients, and SynaptiVerse administrators appropriate dashboards.

Core positioning:

> Right care. Right facility. Right time.

Important clinical boundary:

> SynaptiVerse supports clinicians and patients. It does not diagnose, replace a clinician, or replace emergency services.

## MVP scope and safety boundary

Build a convincing, functional demonstration and a sound architecture, not a certified medical device or production clinical decision system.

- Use a deterministic, explainable, configurable rules engine with fictional demo rules for triage.
- Label all triage outputs as recommendations requiring clinical validation.
- Do not generate diagnoses.
- Do not claim medical accuracy, regulatory approval, guaranteed wait-time reductions, or guaranteed outcomes.
- Never allow card payment, HMO verification, appointment acceptance, or registration to delay emergency guidance.
- Do not encode personal or health information in QR codes.
- Use only fictional patients and health information in seed data.
- Make clinical thresholds configurable and clearly mark them as placeholders requiring approval by qualified Nigerian clinicians.

## User roles

Implement role-based access for:

1. **Patient**
2. **Doctor/Specialist**
3. **Clinic or Hospital Staff**
4. **Clinic or Hospital Administrator**
5. **HMO Staff/Administrator**
6. **SynaptiVerse Operations Administrator**
7. **SynaptiVerse Compliance/Security Reviewer**

A doctor may belong to more than one facility through separate verified facility memberships. Every action must be evaluated within an active organization context.

## Public website

Build a modern public-facing website that explains the complete network while keeping one clear purpose per section.

### Responsive navigation

- SynaptiVerse logo
- How Routing Works
- Healthcare Providers
- HMOs
- Patients
- Safety
- Sign In
- Primary CTA: **Join the Network**
- Secondary CTA where appropriate: **Find Care**

Use a sticky desktop navigation and a clear accessible mobile menu. Do not overcrowd the header.

### Homepage sections

1. **Hero**
   - Headline: `AI-assisted triage and smart healthcare routing.`
   - Explain that SynaptiVerse connects patients to suitable nearby care using urgency, facility capability, specialist availability, and travel time.
   - CTAs: `Find Care` and `Join the Healthcare Network`.
   - Show a credible product-interface preview rather than generic stock imagery.

2. **How routing works**
   - Guided symptom intake
   - Explainable urgency recommendation
   - Facility and specialist matching
   - Appointment or emergency referral
   - Hospital card check-in
   - Follow-up and patient timeline

3. **Connected ecosystem**
   - Patients
   - Clinics and hospitals
   - Doctors and specialists
   - HMOs

4. **SynaptiVerse Health Access Card**
   - Digital card
   - QR-based verification using an opaque token
   - Paid first issuance using a mock payment adapter
   - Renewal
   - Lost-card blocking and reissue
   - One identity across participating facilities

5. **Cross-hospital specialist support**
   - Secure remote consultation
   - Visiting specialist
   - Patient stabilization and transfer

6. **Safety and trust**
   - Human oversight
   - Consent and access controls
   - Auditability
   - NDPA-aligned privacy design
   - Clear emergency and non-diagnosis boundaries

7. **Closing CTA**
   - `Bring your hospital, clinic, or HMO into the SynaptiVerse network.`

### Design direction

- Modern Nigerian health-technology identity
- Deep navy for trust
- Bright blue or cyan for intelligence and routing
- Teal for successful actions
- Amber and red reserved for urgency and warnings
- Warm off-white surfaces
- Manrope or a comparable display face for headings
- Inter or a comparable highly legible body font
- Generous spacing, rounded panels, restrained shadows, and purposeful motion
- Avoid a generic template appearance
- WCAG 2.2 AA-minded contrast, focus states, semantics, keyboard navigation, and touch targets
- Mobile-first behavior and good performance on low-bandwidth connections

## Application information architecture

### Patient routes

- `/patient/dashboard`
- `/patient/register`
- `/patient/card`
- `/patient/card/payment`
- `/patient/card/renew`
- `/patient/triage`
- `/patient/routing`
- `/patient/appointments`
- `/patient/referrals`
- `/patient/records`
- `/patient/prescriptions`
- `/patient/hmo`
- `/patient/consent`
- `/patient/notifications`
- `/patient/profile`

### Doctor routes

- `/doctor/dashboard`
- `/doctor/requests`
- `/doctor/appointments`
- `/doctor/patients/[patientId]`
- `/doctor/availability`
- `/doctor/shifts`
- `/doctor/specialist-exchange`
- `/doctor/notifications`
- `/doctor/profile`

### Clinic/Hospital routes

- `/facility/dashboard`
- `/facility/referrals`
- `/facility/appointments`
- `/facility/patients`
- `/facility/card-verification`
- `/facility/departments`
- `/facility/services`
- `/facility/specialists`
- `/facility/staff`
- `/facility/shifts`
- `/facility/capacity`
- `/facility/specialist-exchange`
- `/facility/transfers`
- `/facility/analytics`
- `/facility/settings`

### HMO routes

- `/hmo/dashboard`
- `/hmo/members`
- `/hmo/verification`
- `/hmo/authorizations`
- `/hmo/network`
- `/hmo/claims`
- `/hmo/analytics`
- `/hmo/settings`

### SynaptiVerse administration routes

- `/admin/dashboard`
- `/admin/facilities`
- `/admin/verification`
- `/admin/routing-monitor`
- `/admin/clinical-rules`
- `/admin/card-management`
- `/admin/specialist-exchange`
- `/admin/audit`
- `/admin/incidents`
- `/admin/users`
- `/admin/settings`

## Patient registration and health card

During registration collect only necessary information:

- name;
- date of birth;
- sex where clinically relevant;
- phone and optional email;
- address and location permission;
- emergency contact;
- allergies and active medications;
- relevant known conditions;
- guardian details when applicable;
- HMO membership only when the patient has one;
- clear consent and privacy choices.

Generate a global SynaptiVerse patient ID and an opaque QR verification token. The QR code must never contain raw health data. Provide a polished digital card with:

- patient name;
- masked patient number;
- photo placeholder;
- QR code;
- card status;
- issuance and renewal dates;
- masked HMO verification status when applicable.

Implement card states: `PENDING_PAYMENT`, `ACTIVE`, `EXPIRED`, `LOST`, `REVOKED`, and `REISSUED`.

Use a mock payment adapter for issuance, renewal, and replacement. Emergency routing must remain accessible regardless of card or payment status.

## Optional HMO membership

Ask: `Are you registered with an HMO?`

If `No`:

- mark the patient as self-pay/no HMO registered;
- allow full registration, card issuance, triage, and routing;
- allow HMO details to be added later.

If `Yes`, collect only:

- HMO provider;
- member/enrollee ID;
- plan name;
- employer or scheme when applicable;
- expiry date;
- optional HMO-card upload;
- consent to verify and share necessary administrative information.

Implement membership states: `PENDING`, `VERIFIED`, `INACTIVE`, `EXPIRED`, and `FAILED`.

For routine cases, HMO network status may influence ranking after clinical suitability. For severe cases, clinical capability, specialist availability, acceptance, and travel time must take priority. HMO approval must run in parallel and never block emergency care.

HMOs should see only the minimum information required for eligibility, authorization, service category, provider, claim, and payment. Do not expose complete clinical notes by default.

## Guided triage

Build a multi-step, accessible intake experience that captures:

- main complaint;
- symptom duration;
- severity reported by the patient;
- red-flag answers;
- allergies;
- active medications;
- relevant conditions;
- age and sex when relevant to the configured rules;
- current location or manually entered location.

Output:

- an urgency band such as `ROUTINE`, `PRIORITY`, `URGENT`, or `EMERGENCY`;
- recommended specialty or service;
- an explanation showing which answers influenced the recommendation;
- an explicit statement that the output is not a diagnosis;
- a human-review and correction path.

Keep the rules engine separate from UI and persistence. Add unit tests for every demo rule and boundary condition.

## Facility routing engine

Facilities must maintain:

- organization type: clinic, primary care, secondary hospital, tertiary hospital, diagnostic centre, or specialist centre;
- verified geographic coordinates;
- operating hours and current open/closed status;
- emergency capability;
- departments and services;
- equipment/capability flags;
- specialist roster and on-call status;
- appointment and treatment capacity;
- acceptance status for new referrals;
- supported HMOs and plans;
- accessibility and contact details.

### Routing principles

Use hard eligibility rules before scoring.

For routine and priority cases:

1. Required service or specialty must be available.
2. Facility must be open or have a suitable future appointment.
3. Capacity must be available.
4. Rank by estimated travel time, clinical fit, availability, optional HMO coverage, and patient preference.

For urgent or severe cases:

1. Emergency capability and clinical suitability are mandatory.
2. Required specialist or service availability is prioritized.
3. Facility acceptance and travel time are prioritized over HMO coverage.
4. If a specialist-capable destination cannot be reached safely, identify a nearer stabilization-capable facility and create a transfer pathway to the specialist centre.
5. Never wait for appointment booking, card payment, or HMO approval before showing emergency guidance.

Do not invent clinical travel-time thresholds. Make them administrator-configurable placeholders requiring clinical governance approval.

When no map API key is present, calculate seeded distances using latitude/longitude and the Haversine formula, show a clear ranked facility list, and provide a map adapter interface. Do not block the MVP on a third-party map service.

Store an explainable routing decision containing considered facilities, exclusion reasons, scoring factors, selected facility, and any authorized human override.

## Routing to a hospital where the patient is not registered

The patient must not create another SynaptiVerse account.

1. Send the receiving facility a minimal pending-referral notice.
2. Obtain patient authorization for non-emergency sharing.
3. Let the facility accept or decline.
4. On acceptance, create a `LocalPatientIdentity` that links:
   - global SynaptiVerse patient ID;
   - facility ID;
   - facility medical-record number;
   - registration status and timestamps.
5. At arrival, scan the Health Access Card and verify with PIN, OTP, or staff-assisted identity verification.
6. Convert the referral to an active encounter and notify the assigned care team.
7. Do not automatically merge possible duplicates. Send uncertain matches to authorized staff review.

For a non-participating hospital, generate a printable and downloadable external referral package with a QR verification link, minimal care summary, urgency, required specialty, and contact details.

## Doctor assignment and notifications

Each doctor must have a verified `DoctorFacilityMembership` containing:

- doctor ID;
- facility ID;
- department;
- specialty;
- active/verified status;
- shift or on-call status;
- current availability;
- appointment capacity;
- notification preferences.

Always select by `facilityId` before specialty. A doctor at Hospital B must not receive Hospital A's ordinary appointment notification.

Eligibility logic:

```text
membership.facilityId == referral.facilityId
AND membership.status == VERIFIED
AND specialty matches
AND doctor is on shift or on call
AND doctor is available
AND doctor has capacity
```

### Routine appointment assignment

1. Select the eligible doctor with the lowest workload or next round-robin position.
2. Notify one doctor first.
3. Allow accept or decline with a reason.
4. If declined or unanswered after a facility-configured interval, notify the next eligible doctor.
5. Escalate to the department administrator if no doctor accepts.

### Urgent assignment

1. Notify the eligible on-duty specialty pool and the emergency/triage desk.
2. Use an atomic database transaction so only the first valid acceptance succeeds.
3. Immediately close the action for other doctors.
4. Do not let notification acknowledgement delay emergency stabilization.

Implement notification states: `CREATED`, `QUEUED`, `DELIVERED`, `READ`, `ACKNOWLEDGED`, `ACCEPTED`, `DECLINED`, `ESCALATED`, and `EXPIRED`.

Implement working in-app notifications and browser notifications where supported. Provide mock adapters for SMS, email, and mobile push. Lock-screen messages must not expose diagnoses or detailed symptoms.

## Cross-hospital specialist support

Name the module **SynaptiVerse Specialist Exchange**.

Support three modes:

1. `REMOTE_CONSULTATION`
2. `VISITING_SPECIALIST`
3. `PATIENT_TRANSFER`

Workflow:

1. Hospital A creates a request specifying specialty, urgency, clinical question, available equipment, available supporting staff, desired mode, and patient-sharing authorization.
2. SynaptiVerse searches verified specialists whose organizations allow external support.
3. Hospital B's authorized administrator reviews whether it can release the specialist.
4. The specialist accepts, declines, requests more information, changes the recommended support mode, or recommends transfer.
5. Hospital A grants case-scoped, time-limited access to the minimum necessary data.
6. The specialist documents advice or treatment.
7. Hospital A's attending doctor records the resulting plan.
8. Close the request with outcome, time, costs, authorization, and audit events.

Decision rule:

- If Hospital A has the equipment, staff, and safe treatment capacity but lacks expertise, use remote or visiting support.
- If Hospital A lacks essential equipment, theatre, intensive care, diagnostics, medicines, or supporting personnel, stabilize and transfer the patient.
- Never present specialist travel as a substitute for a medically necessary transfer.

For an on-site procedure, represent credential verification, temporary facility authorization, professional-indemnity confirmation, and hospital-to-hospital agreement as required administrative gates. Do not imply that the software itself grants legal clinical privileges.

For cross-hospital notification:

- the specialist at Hospital B receives a distinct `EXTERNAL_SUPPORT_REQUEST`, not an ordinary Hospital A appointment;
- Hospital B must approve release where required;
- the specialist enters a clearly labeled Hospital A consultation context;
- access ends when the case closes;
- the referring Hospital A doctor receives status updates;
- full audit logging is mandatory.

## Health-information flow

Use a hybrid model:

- each hospital remains the primary source of truth for its full clinical record;
- SynaptiVerse stores platform identity, consent, card, triage, routing, appointments, referrals, notifications, and a patient-facing shared-care summary;
- hospitals release approved summaries, results, prescriptions, referrals, and follow-up information to the patient through SynaptiVerse;
- HMOs receive only necessary administrative and authorization information;
- SynaptiVerse support staff do not have routine access to clinical content.

Model FHIR-compatible concepts where practical, including:

- Patient
- Consent
- QuestionnaireResponse
- Appointment
- Encounter
- Condition
- Observation
- DiagnosticReport
- MedicationRequest
- CarePlan
- DocumentReference
- PractitionerRole
- AuditEvent

Do not attempt a full FHIR server unless the existing repository already has one. Use an internal domain model with documented FHIR mappings and adapter boundaries.

## Hospital-to-patient record release

1. Doctor creates or updates a clinical record in the hospital context.
2. Doctor signs or submits it.
3. Authorized hospital workflow validates and releases the patient-facing content.
4. SynaptiVerse updates the patient's timeline.
5. Send a privacy-safe notification such as `You have a new update from your hospital.`
6. Require authentication before showing clinical content.
7. Let patients view, download, and request correction of information.
8. Preserve record versions; do not silently overwrite signed information.

Support patient-facing objects for:

- encounter summary;
- diagnosis where confirmed and approved for release;
- laboratory and imaging result summaries;
- prescriptions and instructions;
- discharge instructions;
- referrals;
- follow-up appointments.

## Permissions

Implement least-privilege RBAC plus organization and relationship checks.

| Actor | Default access |
| --- | --- |
| Patient | Own card, profile, consent, appointments, referrals, released records, HMO status, and access history |
| Assigned doctor | Relevant information for assigned or actively treated patients within the correct facility context |
| Receptionist | Identity verification, card, appointment, check-in, and payment status; no unrestricted clinical notes |
| Hospital administrator | Facility operations, staff, capacity, referrals, and aggregate analytics; no routine access to detailed clinical notes |
| HMO staff | Eligibility, authorization, covered service, provider, and claim information only |
| SynaptiVerse operations | Platform and routing metadata; no routine clinical-content access |
| Compliance reviewer | Audit and policy evidence using masked data wherever possible |
| Triage engine | Minimum required attributes for the current assessment; no secondary model training by default |

Add a controlled `BREAK_GLASS` emergency-access path that requires a reason, is time limited, generates high-priority audit events, and appears in the patient's access history when legally and clinically appropriate.

## Data model

Create normalized models or equivalent domain entities for at least:

- User
- Session
- Role
- Organization
- Facility
- FacilityLocation
- FacilityCapability
- FacilityHmoContract
- Department
- DoctorProfile
- DoctorCredential
- DoctorFacilityMembership
- Shift
- Availability
- CapacitySnapshot
- PatientProfile
- GuardianRelationship
- HealthAccessCard
- CardPayment
- HmoProvider
- PatientHmoMembership
- HmoAuthorization
- ConsentRecord
- TriageAssessment
- TriageAnswer
- RoutingDecision
- RoutingCandidate
- Referral
- LocalPatientIdentity
- Appointment
- AppointmentAssignment
- EncounterSummary
- ClinicalDocument
- Prescription
- Notification
- NotificationDelivery
- SpecialistSupportRequest
- SpecialistSupportResponse
- TransferRecord
- AuditEvent
- Incident

Include stable IDs, organization scoping, statuses, created/updated timestamps, relevant actor IDs, and soft deletion where appropriate. Add indexes for facility, patient, doctor membership, appointment status, urgency, and notification queries.

## API and service boundaries

Organize business logic into testable services rather than page components:

- Identity and access service
- Patient and card service
- Consent service
- Triage service
- Facility-directory service
- Routing service
- Referral service
- Appointment service
- Notification service
- HMO service
- Specialist Exchange service
- Shared-care-record service
- Audit and incident service
- Integration adapters

Use server-side authorization on every mutation and sensitive query. Never rely only on hidden buttons or client-side role checks.

## Security, privacy, and governance requirements

Design toward the Nigeria Data Protection Act and current NDPC guidance, but do not claim legal compliance or certification.

Implement or clearly scaffold:

- explicit purpose and consent records;
- lawful-basis metadata where relevant;
- data minimization;
- organization-scoped RBAC;
- multi-factor authentication hooks for staff;
- encryption in transit and documented encryption-at-rest expectations;
- opaque identifiers in URLs where practical;
- no personal or health data in application logs;
- immutable or append-only audit events for sensitive actions;
- patient access history;
- retention and deletion-policy configuration;
- consent withdrawal and future-sharing controls;
- export and correction-request flows;
- guardian flows for children or persons lacking capacity;
- cross-border data-transfer configuration notes;
- breach and incident runbook placeholders;
- a Data Privacy Impact Assessment checklist in project documentation.

Use fake data only. Add a clear security review checklist to the README. Mark features that require Nigerian clinical, legal, HMO, and information-security review before production.

## Seed data and demo scenarios

Seed at least:

### Hospital A

- General hospital
- Emergency stabilization capability
- General medicine department
- Doctor A working an active shift
- Limited specialist capability
- At least one supported HMO

### Hospital B

- Specialist/tertiary hospital
- Emergency department
- Cardiology and neurology services
- Doctor B as an available specialist
- Cross-hospital support enabled
- At least one supported HMO

### Patients

- Patient without an HMO
- Patient with a verified HMO
- Patient with a pending HMO verification
- Patient with an active health card
- Patient with an expired or lost card

Build clickable demo flows for:

1. Routine self-pay patient registration, card issuance, triage, routing to Hospital A, local registration, Doctor A notification, acceptance, check-in, and released care summary.
2. Patient with a verified HMO routed to an appropriate in-network facility.
3. Severe fictional case where clinical capability requires Hospital B and Doctor B is notified.
4. Patient routed to a facility where they were not previously registered; create and display the local medical-record-number mapping.
5. Hospital A requests Doctor B through Specialist Exchange for a secure remote consultation.
6. Hospital A lacks essential capability, so the specialist recommends stabilization and transfer to Hospital B.
7. No eligible doctor accepts an appointment; the request escalates to the department administrator.
8. Lost card is revoked and reissued without changing the patient's global identity.

## Dashboard requirements

### Patient dashboard

- Health Access Card
- Start triage
- Current routing recommendation
- Upcoming appointments
- Referrals and transfer status
- Released health timeline
- Prescriptions
- HMO status
- Consent controls
- Notifications
- Report lost card, renew, or reissue

### Doctor dashboard

- Active facility context
- Today's appointments
- Pending requests
- Urgent referrals
- Checked-in patients
- Specialist Exchange requests
- Availability and shift status
- Notification centre
- Accept, decline, request reassignment, and document consultation

### Facility dashboard

- Live referral queue
- Appointment oversight
- Doctor and specialist roster
- Shift and availability management
- Capacity status
- Card verification and check-in
- New-patient local registration
- Specialist Exchange and transfers
- HMO authorization status
- Routing and operational analytics
- Audit-sensitive administrative actions

### HMO dashboard

- Member verification
- Facility network
- Authorization queue
- Coverage decisions
- Claims placeholders
- Utilization and cost analytics using fictional data
- No unrestricted clinical-note access

### SynaptiVerse administrator dashboard

- Facility onboarding and verification
- Capability and specialist-directory quality
- Routing monitor with explanation and overrides
- Card lifecycle management
- Clinical-rule configuration with approval status
- Specialist Exchange oversight
- Security and access audit
- Incident management
- De-identified network analytics

## UX requirements

- Every status must be understandable without relying only on color.
- Use confirmation dialogs for consequential actions such as declining an urgent referral, revoking a card, transferring a patient, or using break-glass access.
- Show empty, loading, success, error, offline, and permission-denied states.
- Use clear plain-language copy suitable for patients with different levels of health literacy.
- Keep emergency warnings prominent and concise.
- Display why a hospital was recommended: travel time, capability, specialist, capacity, and HMO status.
- Make mobile dashboards usable, not merely compressed desktop layouts.
- Protect sensitive information from accidental display in notifications and shared screens.

## Analytics

Use fictional data and avoid misleading clinical-performance claims. Provide operational metrics such as:

- referrals by status;
- average referral-acceptance time;
- appointments by department;
- doctor workload;
- facility capacity;
- routing exclusions and reasons;
- HMO authorization status;
- specialist-support requests by mode;
- transfer completion status;
- card issuance, renewal, loss, and reissue;
- notification delivery and acknowledgement.

Do not display clinical efficacy or outcome claims without validated data.

## Testing and acceptance criteria

Add meaningful automated tests for:

1. Facility hard-eligibility rules.
2. Non-severe ranking with and without HMO membership.
3. Severe routing that prioritizes capability and specialist availability over HMO status.
4. Stabilization-plus-transfer fallback.
5. Doctor selection scoped by facility ID.
6. Doctor B not receiving Hospital A's normal appointment.
7. Atomic first-accept locking for urgent assignments.
8. Escalation when a doctor declines or does not respond.
9. Global patient ID to local hospital record mapping.
10. QR token containing no health information.
11. Lost-card revocation and reissue.
12. HMO minimum-data access.
13. Cross-hospital specialist request authorization and expiry.
14. Role and organization isolation.
15. Consent enforcement and audit-event creation.
16. Patient release of hospital-approved records.

Essential end-to-end tests should cover one patient journey, one doctor assignment, one new-facility registration, one HMO verification, and one Specialist Exchange case.

Before finishing:

- run formatting;
- run linting;
- run type checking;
- run unit and integration tests;
- run the production build;
- fix failures rather than merely reporting them;
- verify the key pages at desktop and mobile widths;
- verify there is no obvious horizontal overflow;
- verify keyboard navigation and visible focus states on primary flows.

## Documentation and deliverables

Deliver:

1. Working application source code.
2. Database schema and migrations.
3. Seed script and demo accounts for every role.
4. `.env.example`.
5. Clear setup and run instructions.
6. Architecture overview.
7. Role and permission matrix.
8. Routing-engine explanation.
9. Notification and escalation design.
10. Health-information-flow diagram.
11. Specialist Exchange workflow.
12. FHIR mapping notes.
13. Security, privacy, DPIA, clinical-governance, and production-readiness checklists.
14. Test summary and known limitations.

## Definition of done

The project is complete when a reviewer can run it locally and demonstrate this continuous journey:

> Patient registration → Health Access Card → optional HMO verification → guided triage → explainable suitable-facility routing → referral acceptance → new-facility local registration → correct doctor notification → appointment acceptance → card check-in → hospital-approved patient record → follow-up.

The reviewer must also be able to demonstrate:

> Hospital A requests specialist support → Hospital B approves → Doctor B accepts in a cross-hospital context → patient information is shared with scoped access → remote/visiting support or transfer is recorded → both hospitals and the patient receive appropriate status updates.

Keep the implementation polished and credible, but clearly label all simulated clinical, payment, HMO, mapping, notification, and EHR behavior. Favor safe defaults, transparent logic, strong organization boundaries, and working end-to-end flows over speculative complexity.
