import Link from 'next/link';
import { ArrowRight, Database, GitBranch, Server, ShieldCheck } from 'lucide-react';
import { Callout, CodeBlock, DocsPage, Section } from '@/components/developers/DocsContent';
import { quickLinks, repositoryTree } from '@/components/developers/docs-data';

export default function DevelopersHomePage() {
  return <DocsPage eyebrow="Developer documentation" title="Build coordinated care workflows with ClinicalFlow." description="The engineering guide to the repository, FastAPI service, Next.js portals, tenant model, deployments and integration boundaries.">
    <div className="grid gap-3 sm:grid-cols-2">{quickLinks.map((item) => <Link key={item.href} href={item.href} className="group rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition hover:-translate-y-0.5 hover:border-[#d8ee72]/35"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#d8ee72]/10 text-[#d8ee72]"><item.icon className="h-5 w-5" /></span><span className="mt-5 flex items-center justify-between font-black text-white">{item.label}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></span></Link>)}</div>

    <Section title="What ClinicalFlow is">
      <p>ClinicalFlow is a multi-tenant healthcare coordination platform. It connects public and authenticated triage, clinical tickets, facility routing, queues, appointments, referrals, laboratory, pharmacy, insurance and public-health workflows without treating automated triage as a diagnosis.</p>
      <div className="grid gap-4 md:grid-cols-2"><Feature icon={Server} title="FastAPI backend">Domain-organized routers, async SQLAlchemy, Alembic migrations and role-aware authorization.</Feature><Feature icon={Database} title="PostgreSQL data plane">A tenant-aware relational model hosted on Supabase in deployed environments.</Feature><Feature icon={GitBranch} title="Next.js portals">Purpose-built interfaces for patients, hospitals, specialists, nurses, pharmacies, labs, insurers and government teams.</Feature><Feature icon={ShieldCheck} title="Security boundaries">HTTP-only sessions, workspace selection, consent records, audit history and explicit production safety checks.</Feature></div>
    </Section>

    <Section title="Get running locally">
      <p>Run the API and frontend in separate terminals. The backend defaults to a local development database; shared environments should use PostgreSQL with Alembic.</p>
      <CodeBlock title="Terminal 1 · Backend">{`cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=$PWD python -m alembic upgrade head
PYTHONPATH=$PWD python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`}</CodeBlock>
      <CodeBlock title="Terminal 2 · Frontend">{`cd frontend
npm install
cp .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000`}</CodeBlock>
      <Callout title="Local URLs" tone="success"><p>Frontend: <code>http://127.0.0.1:3000</code> · API: <code>http://127.0.0.1:8000</code> · Swagger: <code>http://127.0.0.1:8000/docs</code></p></Callout>
    </Section>

    <Section title="Repository at a glance"><CodeBlock title="Project tree">{repositoryTree}</CodeBlock><p>Continue to <Link href="/developers/project-structure" className="font-bold text-[#d8ee72]">Project breakdown</Link> for ownership and module boundaries.</p></Section>

    <Section id="security-boundaries" title="Production boundaries">
      <p>Before a real clinical launch, configure provider credentials, durable background delivery, monitoring, backups, restore drills, privacy review, penetration testing and clinical governance. Use synthetic data in free-tier staging environments.</p>
      <Callout title="Clinical safety boundary">Triage output is decision support, not a confirmed diagnosis. Qualified clinicians and verified facilities remain responsible for clinical decisions.</Callout>
    </Section>
  </DocsPage>;
}

function Feature({ icon: Icon, title, children }: { icon: typeof Server; title: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><Icon className="h-5 w-5 text-[#d8ee72]" /><h3 className="mt-4 font-black text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-white/48">{children}</p></div>;
}

