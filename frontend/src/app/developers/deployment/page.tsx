import { Cloud, GitBranch, Laptop, ShieldCheck } from 'lucide-react';
import { Callout, CodeBlock, DocsPage, Section } from '@/components/developers/DocsContent';

export default function DeploymentPage() {
  return <DocsPage eyebrow="Build" title="Deployments and environments" description="Keep local, staging and production isolated across branches, frontend URLs, backend services, databases and secrets.">
    <div className="grid gap-4 md:grid-cols-3"><Environment icon={Laptop} title="Local" branch="feature/*" detail="Next.js + FastAPI + local PostgreSQL" /><Environment icon={GitBranch} title="Staging" branch="staging" detail="Vercel + Render + staging Supabase" /><Environment icon={Cloud} title="Production" branch="main" detail="Vercel + Render + production Supabase" /></div>

    <Section title="Environment matrix">
      <div className="overflow-x-auto rounded-2xl border border-white/10"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-white/[0.04] text-white"><tr><th className="p-4">Environment</th><th className="p-4">Frontend</th><th className="p-4">Backend</th><th className="p-4">Database</th></tr></thead><tbody className="text-white/52"><tr className="border-t border-white/10"><td className="p-4 font-bold text-white">Production</td><td className="p-4">clinicalflow-one.vercel.app</td><td className="p-4">clinicalflow-tnq5.onrender.com</td><td className="p-4">Production Supabase</td></tr><tr className="border-t border-white/10"><td className="p-4 font-bold text-white">Staging</td><td className="p-4">clinicalflow-staging.vercel.app</td><td className="p-4">clinicalflow-backend-staging.onrender.com</td><td className="p-4">Staging Supabase</td></tr><tr className="border-t border-white/10"><td className="p-4 font-bold text-white">Local</td><td className="p-4">localhost:3000</td><td className="p-4">127.0.0.1:8000</td><td className="p-4">Local PostgreSQL</td></tr></tbody></table></div>
      <Callout title="Never share databases across environments">Preview or staging code must never receive the production <code>DATABASE_URL</code>. Staging contains synthetic data and uses independent tenant IDs and secrets.</Callout>
    </Section>

    <Section title="Render backend">
      <CodeBlock title="Render service settings">{`Root Directory: [leave blank]
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check: /health`}</CodeBlock>
      <CodeBlock title="Production variables">{`APP_ENVIRONMENT=production
DATABASE_URL=<SUPABASE_SESSION_POOLER_URL>
AUTO_CREATE_SCHEMA=false
PLATFORM_TENANT_ID=<DEDICATED_UUID>
SESSION_SECRET=<RANDOM_SECRET>
CHANNEL_WEBHOOK_SECRET=<RANDOM_SECRET>
CORS_ORIGINS=https://clinicalflow-one.vercel.app
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none
SKIP_PHONE_VERIFICATION=false
ENABLE_TEST_FIXTURES=false
ENABLE_DEMO_CONTENT=false
DEBUG=false`}</CodeBlock>
    </Section>

    <Section title="Vercel frontend">
      <p>Set the Vercel root directory to <code>frontend</code>. The frontend needs only the public API address:</p>
      <CodeBlock title="Vercel Config variable">{`NEXT_PUBLIC_API_BASE_URL=https://clinicalflow-tnq5.onrender.com`}</CodeBlock>
      <p><code>NEXT_PUBLIC_API_BASE_URL</code> is safe to expose because browsers must know where to send requests. Database URLs, signing secrets and provider tokens must remain backend secrets.</p>
    </Section>

    <Section title="Release flow">
      <ol className="space-y-4">{['Merge reviewed feature branches into staging.', 'Wait for staging backend and frontend deployments.', 'Run backend tests and Playwright against staging.', 'Confirm Alembic is at head and staging health reports database connected.', 'Open a pull request from staging into main.', 'Merge only after checks and review pass.', 'Watch production migration and startup logs.', 'Run health and non-destructive production smoke tests.'].map((step, index) => <li key={step} className="flex gap-4"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-[#d8ee72]/30 text-xs font-black text-[#d8ee72]">{index + 1}</span><span className="pt-0.5">{step}</span></li>)}</ol>
    </Section>

    <Section title="Production safety checks">
      <div className="grid gap-3 sm:grid-cols-2"><Safety>PostgreSQL is required; deployed SQLite is rejected.</Safety><Safety>Automatic schema creation is disabled; Alembic owns migrations.</Safety><Safety>Cookies are secure and use an intentional SameSite policy.</Safety><Safety>CORS contains exact approved HTTPS origins.</Safety><Safety>Demo content and fixed credentials are disabled.</Safety><Safety>Phone-verification bypass remains disabled.</Safety></div>
      <Callout title="Free-tier reality">Free infrastructure can sleep, pause or omit continuous workers. Upgrade and add monitoring, backups and restore drills before real patient reliance.</Callout>
    </Section>
  </DocsPage>;
}

function Environment({ icon: Icon, title, branch, detail }: { icon: typeof Cloud; title: string; branch: string; detail: string }) { return <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><Icon className="h-5 w-5 text-[#d8ee72]" /><h2 className="mt-4 font-black text-white">{title}</h2><code className="mt-2 block text-xs text-[#d8ee72]">{branch}</code><p className="mt-2 text-sm leading-6 text-white/45">{detail}</p></div>; }
function Safety({ children }: { children: React.ReactNode }) { return <div className="flex gap-3 rounded-xl border border-white/10 p-4 text-sm text-white/55"><ShieldCheck className="h-5 w-5 shrink-0 text-[#d8ee72]" />{children}</div>; }

