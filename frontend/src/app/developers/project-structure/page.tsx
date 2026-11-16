import { Boxes, Database, FolderTree, TestTube2 } from 'lucide-react';
import { Callout, CodeBlock, DocsPage, Section } from '@/components/developers/DocsContent';
import { repositoryTree } from '@/components/developers/docs-data';

const routeDomains = ['auth', 'signup', 'hospitals', 'tickets', 'appointments', 'billing', 'public', 'referrals', 'laboratory', 'pharmacy', 'insurance', 'government', 'terminology', 'patients', 'specialists', 'notifications', 'platform'];

export default function ProjectStructurePage() {
  return <DocsPage eyebrow="Start here" title="Project breakdown" description="How the monorepo is organized, where new code belongs, and which layers own HTTP, domain, persistence and UI behavior.">
    <Section title="Repository map"><CodeBlock title="Repository">{repositoryTree}</CodeBlock></Section>

    <Section title="Backend ownership">
      <div className="grid gap-4 md:grid-cols-2"><Layer icon={FolderTree} title="Routes"><code>backend/app/routes/</code> owns HTTP contracts, request dependencies and response orchestration. Each domain has its own package.</Layer><Layer icon={Database} title="Models"><code>backend/app/models/</code> owns SQLAlchemy persistence entities and relationships. Alembic migrations remain the schema history.</Layer><Layer icon={Boxes} title="Services"><code>backend/app/services/</code> owns reusable auth, routing, provider, queue and integration behavior that is not HTTP-specific.</Layer><Layer icon={TestTube2} title="Tests"><code>backend/tests/</code> covers route contracts, authorization, clinical workflows, migrations and regressions.</Layer></div>
      <div className="flex flex-wrap gap-2">{routeDomains.map((domain) => <code key={domain} className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white/65">routes/{domain}</code>)}</div>
      <Callout title="Keep route modules narrow">Place authentication behavior under <code>routes/auth</code>, signup under <code>routes/signup</code>, and domain endpoints in their matching package. Move shared business rules into services or focused helpers instead of rebuilding a monolithic route file.</Callout>
    </Section>

    <Section title="Frontend ownership">
      <p>The frontend uses the Next.js App Router. URL-level screens belong under <code>frontend/src/app</code>; shared interface modules belong under <code>frontend/src/components</code>; API and auth clients belong under <code>frontend/src/lib</code>.</p>
      <div className="overflow-hidden rounded-2xl border border-white/10"><Row name="app/dashboard" owner="Patient portal routes" /><Row name="app/hospital" owner="Facility workspace routes" /><Row name="app/specialist" owner="Specialist workspace routes" /><Row name="app/nurse" owner="Nursing workspace routes" /><Row name="app/pharmacy" owner="Pharmacy workspace routes" /><Row name="app/lab" owner="Laboratory workspace routes" /><Row name="app/hmo" owner="Insurance workspace routes" /><Row name="app/moh" owner="Government workspace routes" /><Row name="components" owner="Reusable UI and domain widgets" /><Row name="lib/api.ts + lib/auth.ts" owner="Backend transport and sessions" /></div>
    </Section>

    <Section title="Change checklist">
      <ol className="list-decimal space-y-3 pl-5"><li>Choose the owning domain before adding a route or page.</li><li>Update schemas and models deliberately; add an Alembic migration for persisted changes.</li><li>Enforce tenant and role boundaries on the backend, not only in the UI.</li><li>Add focused backend tests and a browser path for critical user journeys.</li><li>Run type checking, backend tests and the production build before promotion.</li></ol>
      <CodeBlock title="Verification">{`cd backend && .venv/bin/python -m pytest -q
cd ../frontend && npm run typecheck
npm run build`}</CodeBlock>
    </Section>
  </DocsPage>;
}

function Layer({ icon: Icon, title, children }: { icon: typeof Boxes; title: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><Icon className="h-5 w-5 text-[#d8ee72]" /><h3 className="mt-4 font-black text-white">{title}</h3><div className="mt-2 text-sm leading-6 text-white/48">{children}</div></div>;
}

function Row({ name, owner }: { name: string; owner: string }) {
  return <div className="grid gap-1 border-b border-white/10 p-4 last:border-0 sm:grid-cols-[220px_1fr]"><code className="text-sm text-[#d8ee72]">{name}</code><span className="text-sm text-white/48">{owner}</span></div>;
}

