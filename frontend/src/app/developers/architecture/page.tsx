import { ArrowDown, BellRing, Database, Globe2, Server, Smartphone, Workflow } from 'lucide-react';
import { Callout, DocsPage, Section } from '@/components/developers/DocsContent';

export default function ArchitecturePage() {
  return <DocsPage eyebrow="Start here" title="System architecture" description="A service map of how browser portals, channel integrations, FastAPI, PostgreSQL and optional infrastructure coordinate care.">
    <Section title="Request path">
      <div className="grid gap-3"><ArchitectureNode icon={Globe2} title="Next.js frontend · Vercel" detail="Public website and role-specific portals" /><Connector /><ArchitectureNode icon={Server} title="FastAPI backend · Render" detail="Authentication, authorization, workflows and integration boundary" /><Connector /><ArchitectureNode icon={Database} title="PostgreSQL · Supabase" detail="Tenant-aware operational, clinical and audit records" /></div>
      <Callout title="The browser never connects to PostgreSQL">All application data moves through FastAPI. Database credentials and provider secrets remain backend-only.</Callout>
    </Section>

    <Section title="Logical components">
      <div className="grid gap-4 sm:grid-cols-2"><Component icon={Workflow} title="Care coordination engine">Triage creates or enriches tickets, determines urgency and routes toward appropriate specialties and facilities.</Component><Component icon={Database} title="Relational source of truth">PostgreSQL stores accounts, memberships, patients, tickets, appointments, referrals, results, claims and audit history.</Component><Component icon={BellRing} title="Durable outbox">Notification events are committed with domain changes, then delivered by provider adapters and a worker.</Component><Component icon={Smartphone} title="Channel intake">WhatsApp and SMS webhooks normalize inbound messages into the same ticket and scheduling workflows used by the web UI.</Component></div>
    </Section>

    <Section title="Tenant and identity boundaries">
      <div className="grid gap-4 md:grid-cols-3"><Numbered number="01" title="Authenticate">Resolve the account from secure session state.</Numbered><Numbered number="02" title="Select workspace">Confirm an active membership for the requested tenant.</Numbered><Numbered number="03" title="Scope every query">Apply tenant, patient-consent and role constraints before returning data.</Numbered></div>
      <p>A user identity and a workspace are separate concepts. A clinician may have access to more than one facility, while a platform administrator operates under different permissions. Workspace selection must never increase the account's persisted role.</p>
    </Section>

    <Section title="Resilience and optional infrastructure">
      <div className="overflow-hidden rounded-2xl border border-white/10"><ArchitectureRow service="Redis" role="Rate limiting, caching and cross-instance realtime fan-out" fallback="Local degraded mode" /><ArchitectureRow service="Neo4j" role="Knowledge graph routing and terminology relationships" fallback="PostgreSQL/in-process fallback" /><ArchitectureRow service="Worker" role="Outbox delivery and retry processing" fallback="Not started on free production demo" /><ArchitectureRow service="Object storage" role="Private verification documents and clinical files" fallback="Must be configured before uploads" /><ArchitectureRow service="Email / SMS / WhatsApp" role="Verification and operational communications" fallback="Provider adapters required" /></div>
      <Callout title="Free-tier limitation">The current free Render service can sleep and does not run a continuous production worker. Do not claim reliable asynchronous delivery until a monitored worker is deployed.</Callout>
    </Section>

    <Section title="Clinical data flow">
      <ol className="space-y-4">{['A patient describes symptoms through web, WhatsApp or SMS.', 'The backend normalizes intake and applies reviewed routing terminology.', 'A clinical ticket records urgency, specialty and consent-aware context.', 'A facility receives the ticket and makes an explicit acceptance or routing decision.', 'Appointments, encounters, referrals, laboratory and pharmacy events extend the record.', 'Patients and authorized care teams see role-appropriate projections of the same workflow.'].map((step, index) => <li key={step} className="flex gap-4"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#d8ee72] text-xs font-black text-[#073d33]">{index + 1}</span><span className="pt-0.5">{step}</span></li>)}</ol>
    </Section>
  </DocsPage>;
}

function ArchitectureNode({ icon: Icon, title, detail }: { icon: typeof Server; title: string; detail: string }) { return <div className="mx-auto flex w-full max-w-2xl items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.035] p-5"><span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-[#d8ee72]/10 text-[#d8ee72]"><Icon className="h-6 w-6" /></span><div><h3 className="font-black text-white">{title}</h3><p className="mt-1 text-sm text-white/45">{detail}</p></div></div>; }
function Connector() { return <ArrowDown className="mx-auto h-5 w-5 text-white/25" />; }
function Component({ icon: Icon, title, children }: { icon: typeof Workflow; title: string; children: React.ReactNode }) { return <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><Icon className="h-5 w-5 text-[#d8ee72]" /><h3 className="mt-4 font-black text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-white/48">{children}</p></div>; }
function Numbered({ number, title, children }: { number: string; title: string; children: React.ReactNode }) { return <div className="rounded-2xl border border-white/10 p-5"><span className="text-xs font-black text-[#d8ee72]">{number}</span><h3 className="mt-3 font-black text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-white/45">{children}</p></div>; }
function ArchitectureRow({ service, role, fallback }: { service: string; role: string; fallback: string }) { return <div className="grid gap-2 border-b border-white/10 p-4 last:border-0 md:grid-cols-[120px_1fr_220px]"><strong className="text-white">{service}</strong><span className="text-sm text-white/52">{role}</span><span className="text-sm text-[#d8ee72]/70">{fallback}</span></div>; }

