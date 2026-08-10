# Codex Build Prompt: SynaptiVerse Global Healthcare Coordination Platform

## Your role

Act as a senior product engineer, UX designer, healthcare-systems architect, security engineer, internationalization specialist, and QA lead. Build a polished, responsive, production-minded MVP of **SynaptiVerse**, an AI-assisted healthcare triage, routing, appointment, health-card, and cross-organization collaboration platform designed for deployment across different health sectors and countries worldwide.

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
5. Use adapters for maps, email, SMS, push notifications, payments, payer/insurer verification, video consultation, hospital EHRs, laboratories, pharmacies, emergency transport, and national or regional health systems. Provide working local mock adapters when real credentials are unavailable.
6. Never hardcode secrets. Add a complete `.env.example`.

## Product vision

SynaptiVerse connects patients, caregivers, clinics, hospitals, doctors, specialists, diagnostic services, pharmacies, emergency transport providers, public-health networks, and payers or insurers in one coordinated care-routing network.

The platform should:

- give every registered patient a secure digital and optional physical **SynaptiVerse Health Access Card**;
- collect symptoms through a guided intake experience;
- produce an explainable urgency and specialty recommendation without claiming to diagnose;
- route a patient to the closest **suitable** provider using clinical capability, urgency, travel time, specialist availability, capacity, operating status, jurisdiction, and optional payer or insurance coverage;
- create and manage appointments;
- notify the correct doctor based on facility, department, specialty, shift, availability, and capacity;
- let a new organization create a local patient record linked to the patient's SynaptiVerse network identity;
- allow healthcare organizations to request specialists from other authorized organizations through remote consultation, visiting-specialist support, or patient transfer;
- return provider-approved care summaries, results, prescriptions, dispensing updates, transport handovers, and follow-up information to the patient;
- give patients, caregivers, clinicians, healthcare facilities, diagnostic services, pharmacies, emergency transport providers, payers or insurers, health networks, and SynaptiVerse administrators appropriate dashboards.

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
- Never allow card payment, insurance verification, appointment acceptance, or registration to delay emergency guidance.
- Do not encode personal or health information in QR codes.
- Use only fictional patients and health information in seed data.
- Make clinical thresholds configurable by jurisdiction and clearly mark them as placeholders requiring approval by qualified local clinicians and health authorities where required.

## Global product architecture

Build SynaptiVerse as a multi-tenant, multi-country, multi-language platform. Do not hardcode one country's healthcare structure, terminology, emergency process, currency, date format, insurance model, clinician-licensing rules, or privacy requirements.

### Global control plane and regional data planes

- Use a global control plane only for non-clinical platform configuration, organization discovery, supported regions, deployment status, and globally unique technical identifiers.
- Keep identifiable patient and clinical information in region-scoped data stores or clearly separated regional partitions.
- Associate sensitive records with `tenantId`, `regionId`, `countryCode`, and data-residency policy.
- Do not automatically replicate identifiable health records across national borders.
- Treat cross-border access and transfer as an explicit, policy-controlled workflow with consent or another approved basis, destination checks, encryption, and audit events.
- A patient may have one SynaptiVerse account while their clinical records, consent directives, and local patient identifiers remain region scoped.

### Country and region configuration

Create a `CountryConfiguration` or `RegionPolicyProfile` that can define:

- ISO country and subdivision codes;
- default language and supported languages;
- locale, time zones, calendars, date and number formats;
- currency and payment-provider adapters;
- metric or other measurement units;
- address and phone-number formats;
- local facility and practitioner identifiers;
- organization types and care levels;
- payer terminology such as HMO, insurer, health plan, national health service, public scheme, or self-pay;
- emergency instructions and verified local emergency contacts;
- patient age and guardian rules;
- consent, retention, access, export, deletion, breach, and data-residency policies;
- clinician licensing and telemedicine jurisdiction rules;
- permitted terminology, coding, EHR, pharmacy, laboratory, and claims adapters.

Never guess or globally hardcode an emergency number. Emergency content must come from verified regional configuration and be reviewable by an authorized regional administrator.

### Internationalization and localization

- Externalize every user-facing string.
- Provide at least English plus one additional fictional/demo locale to prove the architecture.
- Support right-to-left layouts at the component and design-token level even if the initial demo languages are left-to-right.
- Use locale-aware dates, times, currencies, pluralization, names, addresses, and phone numbers.
- Store timestamps in UTC and render them in the user's or facility's active time zone.
- Never assume a Western name order, ZIP code, state, or fixed phone-number length.
- Let regional administrators customize patient-facing terminology without changing application code.

### Global identity and jurisdiction

- Use globally unique internal IDs, but never imply that SynaptiVerse replaces government identity systems or national health identifiers.
- Keep national identifiers optional, encrypted, region scoped, and behind additional access controls.
- Record each clinician's licensed jurisdictions, verified credentials, specialties, facility privileges, and telemedicine permissions.
- A clinician must not receive or accept a cross-border or cross-jurisdiction case unless the configured policy and human authorization permit it.
- Make organization verification, credential verification, and policy approval explicit states rather than assumptions.

## User roles

Implement role-based access for:

1. **Patient**
2. **Doctor/Specialist**
3. **Clinic or Hospital Staff**
4. **Clinic or Hospital Administrator**
5. **Diagnostic Laboratory or Imaging Staff/Administrator**
6. **Pharmacy Staff/Administrator**
7. **Emergency Transport/EMS Staff/Dispatcher**
8. **Payer, Insurer, HMO, or Health-Plan Staff/Administrator**
9. **Health Network or Regional Administrator**
10. **SynaptiVerse Operations Administrator**
11. **SynaptiVerse Compliance/Security Reviewer**

A doctor may belong to more than one facility through separate verified facility memberships. Every action must be evaluated within an active organization context.

## Public website

Build a modern public-facing website that explains the complete network while keeping one clear purpose per section.

### Responsive navigation

- SynaptiVerse logo
- How Routing Works
- Healthcare Providers
- Payers & Health Plans
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
   - Payers, insurers, HMOs, and public health plans
   - Diagnostic laboratories and imaging centres
   - Pharmacies
   - Emergency transport and referral networks

4. **SynaptiVerse Health Access Card**
   - Digital card
   - QR-based verification using an opaque token
   - Region-configurable free or paid first issuance using a mock payment adapter when fees apply
   - Renewal
   - Lost-card blocking and reissue
   - One network identity across approved participating organizations and jurisdictions

5. **Cross-hospital specialist support**
   - Secure remote consultation
   - Visiting specialist
   - Patient stabilization and transfer

6. **Safety and trust**
   - Human oversight
   - Consent and access controls
   - Auditability
   - Region-aware privacy and data-residency design
   - Clear emergency and non-diagnosis boundaries

7. **Closing CTA**
   - `Bring your healthcare organization or care network into SynaptiVerse.`

### Design direction

- Globally inclusive health-technology identity that can be localized without changing the core product
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
- `/patient/coverage`
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

### Payer, insurer, HMO, or health-plan routes

- `/payer/dashboard`
- `/payer/members`
- `/payer/verification`
- `/payer/authorizations`
- `/payer/network`
- `/payer/claims`
- `/payer/analytics`
- `/payer/settings`

Use the active region's configured term in the interface. For example, the same domain module may appear as `HMO`, `Insurer`, `Health Plan`, `Public Scheme`, or `Payer` without changing its data model.

### Diagnostics routes

- `/diagnostics/dashboard`
- `/diagnostics/orders`
- `/diagnostics/specimens`
- `/diagnostics/imaging`
- `/diagnostics/results`
- `/diagnostics/notifications`
- `/diagnostics/settings`

### Pharmacy routes

- `/pharmacy/dashboard`
- `/pharmacy/prescriptions`
- `/pharmacy/dispensing`
- `/pharmacy/inventory`
- `/pharmacy/notifications`
- `/pharmacy/settings`

### Emergency transport routes

- `/transport/dashboard`
- `/transport/requests`
- `/transport/active`
- `/transport/handover`
- `/transport/fleet`
- `/transport/notifications`
- `/transport/settings`

### Health network or regional administration routes

- `/network/dashboard`
- `/network/organizations`
- `/network/practitioners`
- `/network/routing-policy`
- `/network/localization`
- `/network/integrations`
- `/network/compliance`
- `/network/settings`

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
- payer, insurance, public-plan, or HMO membership only when the patient has one;
- clear consent and privacy choices.

Generate a globally unique technical SynaptiVerse network ID plus a region-scoped patient identity and an opaque QR verification token. The QR code must never contain raw health data. Provide a polished digital card with:

- patient name;
- masked patient number;
- photo placeholder;
- QR code;
- card status;
- issuance and renewal dates;
- masked coverage verification status when applicable.

Implement card states: `PENDING_PAYMENT`, `ACTIVE`, `EXPIRED`, `LOST`, `REVOKED`, and `REISSUED`.

Use regional configuration to determine whether issuance, renewal, or replacement is free, publicly funded, payer funded, employer funded, or patient paid. Use a mock payment adapter when fees apply. Emergency routing must remain accessible regardless of card or payment status.

## Optional payer, insurance, public-plan, or HMO membership

Use the active region's configured terminology and ask a localized question such as: `Do you have health coverage or an insurance plan?`

If `No`:

- mark the patient as self-pay or not currently linked to a coverage plan;
- allow full registration, card issuance, triage, and routing;
- allow coverage details to be added later.

If `Yes`, collect only:

- payer, insurer, HMO, public scheme, or health-plan provider;
- member/enrollee ID;
- plan name;
- employer or scheme when applicable;
- expiry date;
- optional plan-card or coverage-document upload;
- consent to verify and share necessary administrative information.

Implement membership states: `PENDING`, `VERIFIED`, `INACTIVE`, `EXPIRED`, and `FAILED`.

For routine cases, payer-network status may influence ranking after clinical suitability. For severe cases, clinical capability, specialist availability, acceptance, and travel time must take priority. Coverage approval must run in parallel and never block emergency care.

Payers and health plans should see only the minimum information required for eligibility, authorization, service category, provider, claim, and payment. Do not expose complete clinical notes by default.

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

- organization type: clinic, primary care, community facility, secondary hospital, tertiary hospital, specialist centre, diagnostic laboratory, imaging centre, pharmacy, emergency transport provider, rehabilitation service, payer, public-health organization, or configured regional type;
- verified geographic coordinates;
- operating hours and current open/closed status;
- emergency capability;
- departments and services;
- equipment/capability flags;
- specialist roster and on-call status;
- appointment and treatment capacity;
- acceptance status for new referrals;
- supported payers, insurers, public schemes, HMOs, and plans;
- accessibility and contact details.

### Routing principles

Use hard eligibility rules before scoring.

For routine and priority cases:

1. Required service or specialty must be available.
2. Facility must be open or have a suitable future appointment.
3. Capacity must be available.
4. Rank by estimated travel time, clinical fit, availability, optional payer-network coverage, and patient preference.

For urgent or severe cases:

1. Emergency capability and clinical suitability are mandatory.
2. Required specialist or service availability is prioritized.
3. Facility acceptance and travel time are prioritized over payer-network coverage.
4. If a specialist-capable destination cannot be reached safely, identify a nearer stabilization-capable facility and create a transfer pathway to the specialist centre.
5. Never wait for appointment booking, card payment, or coverage approval before showing emergency guidance.

Do not invent clinical travel-time thresholds. Make them administrator-configurable placeholders requiring clinical governance approval.

When no map API key is present, calculate seeded distances using latitude/longitude and the Haversine formula, show a clear ranked facility list, and provide a map adapter interface. Do not block the MVP on a third-party map service.

Store an explainable routing decision containing considered facilities, exclusion reasons, scoring factors, selected facility, and any authorized human override.

## Routing to a hospital where the patient is not registered

The patient must not create another SynaptiVerse account.

1. Send the receiving facility a minimal pending-referral notice.
2. Obtain patient authorization for non-emergency sharing.
3. Let the facility accept or decline.
4. On acceptance, create a `LocalPatientIdentity` that links:
   - SynaptiVerse network ID and region-scoped patient ID;
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

- each care-delivery organization remains the primary source of truth for the detailed record it creates;
- SynaptiVerse stores platform identity, consent, card, triage, routing, appointments, referrals, notifications, and a patient-facing shared-care summary;
- hospitals release approved summaries, results, prescriptions, referrals, and follow-up information to the patient through SynaptiVerse;
- payers, insurers, HMOs, and public schemes receive only necessary administrative and authorization information;
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

### Multi-sector clinical exchange

Build the domain and interfaces so a care journey can cross sectors without forcing every organization into a hospital-shaped model:

- A clinician may create a diagnostic order for a laboratory or imaging centre.
- A diagnostic organization may accept the order, track collection or imaging, and release a signed result to the ordering organization and patient.
- A clinician may issue a prescription to the patient.
- An authorized pharmacy may verify the prescription, record dispensing status, and send a patient-safe collection update.
- A facility may request emergency or non-emergency transport, share a minimum handover package, receive an ETA, and record completed handover.
- A public-health or regional-network organization may receive only authorized, appropriately de-identified aggregate data unless a separate lawful case workflow applies.
- Every cross-organization exchange must be purpose limited, relationship checked, consent or policy evaluated, and audited.

Implement one working fictional flow for laboratory results, one for pharmacy dispensing, and one for transport handover. Keep inventory, billing, and national-system integrations shallow but place them behind clear adapters.

## Provider-to-patient record release

1. An authorized clinician or diagnostic professional creates or updates a record in the correct organization context.
2. Doctor signs or submits it.
3. The authorized provider workflow validates and releases the patient-facing content.
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
| Patient | Own card, profile, consent, appointments, referrals, released records, coverage status, and access history |
| Assigned doctor | Relevant information for assigned or actively treated patients within the correct facility context |
| Receptionist | Identity verification, card, appointment, check-in, and payment status; no unrestricted clinical notes |
| Hospital administrator | Facility operations, staff, capacity, referrals, and aggregate analytics; no routine access to detailed clinical notes |
| Diagnostic staff | Orders and case information necessary to collect, perform, validate, and release the requested test or image |
| Pharmacy staff | Valid prescription, patient verification, coverage, and dispensing information necessary for the current order |
| Emergency transport staff | Pickup, destination, urgency, safety needs, ETA, and minimum handover information necessary for transport |
| Payer or health-plan staff | Eligibility, authorization, covered service, provider, and claim information only |
| Network or regional administrator | Organization verification, regional configuration, routing policy, and appropriately de-identified aggregate information |
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
- OrganizationType
- CountryConfiguration
- RegionPolicyProfile
- DataResidencyPolicy
- OrganizationRegionMembership
- Facility
- FacilityLocation
- FacilityCapability
- FacilityPayerContract
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
- PayerOrganization
- CoveragePlan
- PatientCoverage
- PayerAuthorization
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
- DiagnosticOrder
- DiagnosticResult
- MedicationDispense
- TransportRequest
- TransportHandover
- Notification
- NotificationDelivery
- SpecialistSupportRequest
- SpecialistSupportResponse
- TransferRecord
- AuditEvent
- Incident

Include stable IDs, tenant and organization scoping, region and country scoping, statuses, created/updated timestamps, relevant actor IDs, and soft deletion where appropriate. Add indexes for tenant, region, facility, patient, doctor membership, appointment status, urgency, and notification queries.

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
- Payer and coverage service
- Diagnostic-order and result service
- Pharmacy and dispensing service
- Emergency transport and handover service
- Localization and region-policy service
- Specialist Exchange service
- Shared-care-record service
- Audit and incident service
- Integration adapters

Use server-side authorization on every mutation and sensitive query. Never rely only on hidden buttons or client-side role checks.

## Security, privacy, and governance requirements

Design for configurable compliance profiles under applicable national and regional privacy, health-information, telemedicine, clinician-licensing, insurance, medical-device, consumer-protection, and data-residency rules. Do not claim legal compliance, certification, or authorization in any jurisdiction.

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
- region-specific privacy notices, consent language, and age/guardian rules;
- regional storage selection and data-residency enforcement;
- cross-border data-transfer approval, patient notice, destination, and audit controls;
- clinician licence-jurisdiction and facility-privilege checks;
- regional emergency-content verification;
- breach and incident runbook placeholders;
- a Data Privacy Impact Assessment checklist in project documentation.

Use fake data only. Add a clear security review checklist to the README. Mark features that require local clinical, legal, payer, data-protection, cybersecurity, accessibility, localization, and health-authority review before production in each target jurisdiction.

## Seed data and demo scenarios

Seed at least:

### Regional configurations

- Two region profiles with different country codes, locales, time zones, currencies, payer terminology, emergency-content placeholders, retention settings, and data-residency rules
- One English interface configuration and one additional translated demo locale
- One right-to-left layout test configuration, even if it is not populated with full production copy
- Fictional organizations and people only; do not imply live connection to any country's health service

### Hospital A

- General hospital
- Emergency stabilization capability
- General medicine department
- Doctor A working an active shift
- Limited specialist capability
- At least one supported payer or health plan

### Hospital B

- Specialist/tertiary hospital
- Emergency department
- Cardiology and neurology services
- Doctor B as an available specialist
- Cross-hospital support enabled
- At least one supported payer or health plan

### Additional health-sector organizations

- Diagnostic laboratory with fictional test capability
- Imaging centre with fictional modality capability
- Pharmacy with prescription-verification and dispensing enabled
- Emergency transport provider with fictional vehicles and dispatchers
- Payer or public-plan organization
- Regional health-network administrator

### Patients

- Patient without coverage
- Patient with a verified payer or health plan
- Patient with pending coverage verification
- Patient with an active health card
- Patient with an expired or lost card

Build clickable demo flows for:

1. Routine self-pay patient registration, card issuance, triage, routing to Hospital A, local registration, Doctor A notification, acceptance, check-in, and released care summary.
2. Patient with verified coverage routed to an appropriate in-network facility.
3. Severe fictional case where clinical capability requires Hospital B and Doctor B is notified.
4. Patient routed to a facility where they were not previously registered; create and display the local medical-record-number mapping.
5. Hospital A requests Doctor B through Specialist Exchange for a secure remote consultation.
6. Hospital A lacks essential capability, so the specialist recommends stabilization and transfer to Hospital B.
7. No eligible doctor accepts an appointment; the request escalates to the department administrator.
8. Lost card is revoked and reissued without changing the patient's SynaptiVerse network identity.
9. Clinician creates a diagnostic order; a fictional laboratory accepts it and releases a signed result to the patient timeline.
10. Pharmacy verifies and dispenses a fictional prescription and sends a privacy-safe collection update.
11. A facility requests emergency transport; a dispatcher accepts, updates ETA, and records handover.
12. A proposed cross-border record request is held for policy review rather than automatically copying the patient's clinical record.

## Dashboard requirements

### Patient dashboard

- Health Access Card
- Start triage
- Current routing recommendation
- Upcoming appointments
- Referrals and transfer status
- Released health timeline
- Prescriptions
- Coverage or payer status using the active region's terminology
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
- Payer or coverage authorization status
- Routing and operational analytics
- Audit-sensitive administrative actions

### Payer, insurer, HMO, or health-plan dashboard

- Member verification
- Facility network
- Authorization queue
- Coverage decisions
- Claims placeholders
- Utilization and cost analytics using fictional data
- No unrestricted clinical-note access

### Diagnostic dashboard

- Incoming orders
- Collection or imaging status
- Result validation and release
- Ordering clinician and patient notifications
- Organization-scoped audit history

### Pharmacy dashboard

- Prescription verification
- Dispensing queue
- Collection or delivery status
- Coverage status where necessary
- Patient-safe notifications

### Emergency transport dashboard

- Transport request queue
- Urgency, pickup, destination, and minimum safety information
- Dispatcher assignment
- Vehicle and crew availability
- ETA and handover completion

### Health network or regional dashboard

- Organization and practitioner verification
- Country and region configuration
- Localization and emergency-content review
- Routing-policy approval
- Integration status
- De-identified network analytics
- Regional audit and incident oversight

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
- Display why a provider was recommended: travel time, capability, specialist, capacity, and payer-network status where relevant.
- Render language, currency, date, time, units, address, and coverage terminology from regional configuration.
- Test long translated text, right-to-left layout behavior, and locale switching without page reload where practical.
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
- payer or coverage authorization status;
- diagnostic-order and result status;
- pharmacy dispensing status;
- transport assignment, ETA, and handover status;
- operational metrics segmented by region without leaking cross-tenant patient data;
- specialist-support requests by mode;
- transfer completion status;
- card issuance, renewal, loss, and reissue;
- notification delivery and acknowledgement.

Do not display clinical efficacy or outcome claims without validated data.

## Testing and acceptance criteria

Add meaningful automated tests for:

1. Facility hard-eligibility rules.
2. Non-severe ranking with and without payer coverage.
3. Severe routing that prioritizes capability and specialist availability over payer-network status.
4. Stabilization-plus-transfer fallback.
5. Doctor selection scoped by facility ID.
6. Doctor B not receiving Hospital A's normal appointment.
7. Atomic first-accept locking for urgent assignments.
8. Escalation when a doctor declines or does not respond.
9. SynaptiVerse network ID and region-scoped patient ID to local facility record mapping.
10. QR token containing no health information.
11. Lost-card revocation and reissue.
12. Payer minimum-data access.
13. Cross-hospital specialist request authorization and expiry.
14. Role and organization isolation.
15. Consent enforcement and audit-event creation.
16. Patient release of provider-approved records.
17. Locale-aware rendering for dates, time zones, currency, units, names, and addresses.
18. Region and tenant isolation.
19. Cross-border transfer blocked until required policy checks and authorization succeed.
20. Clinician jurisdiction and facility-membership checks.
21. Diagnostic result release, pharmacy dispensing, and transport handover flows.

Essential end-to-end tests should cover one patient journey, one doctor assignment, one new-facility registration, one payer verification, one Specialist Exchange case, one multi-sector order-to-result flow, and one locale switch.

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
13. Country/region configuration guide.
14. Internationalization, localization, and right-to-left readiness notes.
15. Regional data-residency and cross-border-transfer architecture.
16. Security, privacy, DPIA, clinical-governance, and production-readiness checklists.
17. Test summary and known limitations.

## Definition of done

The project is complete when a reviewer can run it locally and demonstrate this continuous journey:

> Patient registration → Health Access Card → optional payer or coverage verification → guided triage → explainable suitable-provider routing → referral acceptance → new-facility local registration → correct clinician notification → appointment acceptance → card check-in → provider-approved patient record → follow-up.

The reviewer must also be able to demonstrate:

> Hospital A requests specialist support → Hospital B approves → Doctor B accepts in a cross-hospital context → patient information is shared with scoped access → remote/visiting support or transfer is recorded → both hospitals and the patient receive appropriate status updates.

The reviewer must also be able to switch regions and locales, demonstrate different payer terminology and currencies, verify that regional patient records remain isolated, and complete one diagnostic, pharmacy, or transport exchange through the shared multi-sector architecture.

Keep the implementation polished and credible, but clearly label all simulated clinical, payment, payer, mapping, notification, EHR, laboratory, pharmacy, transport, and regional-policy behavior. Favor safe defaults, transparent logic, strong tenant and regional boundaries, and working end-to-end flows over speculative complexity.
