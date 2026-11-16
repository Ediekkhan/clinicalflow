import { KeyRound, LockKeyhole, Radio, ShieldCheck } from 'lucide-react';
import { Callout, CodeBlock, DocsPage, ExternalDocLink, Section } from '@/components/developers/DocsContent';
import { apiGroups } from '@/components/developers/docs-data';

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';
const methodStyles: Record<string, string> = {
  GET: 'border-sky-400/20 bg-sky-400/10 text-sky-300',
  POST: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300',
  PATCH: 'border-amber-400/20 bg-amber-400/10 text-amber-300',
  PUT: 'border-violet-400/20 bg-violet-400/10 text-violet-300',
  DELETE: 'border-rose-400/20 bg-rose-400/10 text-rose-300',
};

export default function ApiReferencePage() {
  return <DocsPage eyebrow="Build" title="ClinicalFlow API reference" description="A curated map of the HTTP API. FastAPI OpenAPI remains the executable source of truth for schemas, validation and every registered operation.">
    <div className="grid gap-4 md:grid-cols-3"><InfoCard icon={KeyRound} title="Cookie sessions">Browser clients authenticate with secure HTTP-only access and refresh cookies.</InfoCard><InfoCard icon={ShieldCheck} title="Role authorization">Endpoints enforce account roles and selected tenant workspaces server-side.</InfoCard><InfoCard icon={Radio} title="Live contracts">Swagger and ReDoc are generated directly from the deployed application.</InfoCard></div>

    <Section title="Interactive API documentation">
      <p>Use Swagger when testing requests and ReDoc when reading schemas. Production calls may require an authenticated browser session and a selected workspace.</p>
      <div className="flex flex-wrap gap-3"><a href={`${apiBase}/docs`} target="_blank" rel="noreferrer" className="rounded-full bg-[#d8ee72] px-5 py-3 text-sm font-black text-[#073d33]">Open Swagger UI</a><a href={`${apiBase}/redoc`} target="_blank" rel="noreferrer" className="rounded-full border border-white/15 px-5 py-3 text-sm font-black text-white">Open ReDoc</a><a href={`${apiBase}/openapi.json`} target="_blank" rel="noreferrer" className="rounded-full border border-white/15 px-5 py-3 text-sm font-black text-white">Download OpenAPI JSON</a></div>
      <Callout title="Base URL"><code>{apiBase}</code> is injected through <code>NEXT_PUBLIC_API_BASE_URL</code>. Staging and production must point to their respective backends.</Callout>
    </Section>

    <Section title="Authentication model">
      <p>ClinicalFlow does not expose database credentials to the browser. Sign-in creates server-managed session cookies. Requests that act within a hospital or organization also require an authorized active workspace.</p>
      <CodeBlock title="Authenticated browser request">{`const response = await fetch(
  \`${apiBase}/api/v1/patient/dashboard\`,
  {
    credentials: 'include',
    headers: { 'x-request-id': crypto.randomUUID() }
  }
);`}</CodeBlock>
      <div className="grid gap-3 sm:grid-cols-2"><Boundary icon={LockKeyhole} title="Never store session tokens in localStorage">The frontend uses HTTP-only cookies so JavaScript cannot read the credential.</Boundary><Boundary icon={ShieldCheck} title="Never trust a role from the client">The backend resolves accounts, memberships and tenant scope from persisted authorization state.</Boundary></div>
    </Section>

    {apiGroups.map((group) => <Section key={group.name} title={group.name}><p>{group.description}</p><div className="overflow-hidden rounded-2xl border border-white/10">{group.endpoints.map(([method, path, description]) => <div key={`${method}-${path}`} className="grid gap-3 border-b border-white/10 p-4 last:border-0 md:grid-cols-[72px_minmax(0,1fr)_minmax(180px,0.8fr)] md:items-center"><span className={`w-fit rounded-md border px-2 py-1 text-[10px] font-black ${methodStyles[method]}`}>{method}</span><code className="overflow-x-auto text-sm text-white">{path}</code><span className="text-sm text-white/45">{description}</span></div>)}</div></Section>)}

    <Section title="Errors, idempotency and request tracing">
      <p>Validation errors follow FastAPI response contracts. Domain conflicts generally return <code>409</code>, authorization failures return <code>401</code> or <code>403</code>, and invalid payloads return <code>422</code>. Provider webhooks and mutation retries should use stable event or idempotency identifiers.</p>
      <p>Pass an <code>x-request-id</code> header to correlate a client action with structured backend logs. If omitted, the API generates one and returns it in the response.</p>
      <p>For exact response bodies, required fields and current route coverage, consult the <ExternalDocLink href={`${apiBase}/openapi.json`}>generated OpenAPI contract</ExternalDocLink>.</p>
    </Section>
  </DocsPage>;
}

function InfoCard({ icon: Icon, title, children }: { icon: typeof KeyRound; title: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><Icon className="h-5 w-5 text-[#d8ee72]" /><h2 className="mt-4 font-black text-white">{title}</h2><p className="mt-2 text-sm leading-6 text-white/48">{children}</p></div>;
}

function Boundary({ icon: Icon, title, children }: { icon: typeof ShieldCheck; title: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-white/10 p-4"><div className="flex gap-3"><Icon className="mt-0.5 h-5 w-5 shrink-0 text-[#d8ee72]" /><div><h3 className="font-black text-white">{title}</h3><p className="mt-1 text-sm leading-6 text-white/45">{children}</p></div></div></div>;
}

