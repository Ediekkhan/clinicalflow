import Link from 'next/link';
import { CheckCircle2 } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

const plans = [
  ['Patient', '₦0', 'AI triage, clinic finder, queue tracking, health card'],
  ['Clinic / Specialist', '₦25,000/mo', 'Dashboard, calendar, staff, Kanban, analytics, audit logs'],
  ['Enterprise', 'Custom', 'Multi-branch, HMO integration, API access, SLA, onboarding'],
];

export default function PricingPage() {
  return (
    <main className="bg-slate-50">
      <Navbar />
      <section className="px-6 pb-16 pt-32 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Pricing</p>
        <h1 className="font-display mx-auto mt-3 max-w-3xl text-5xl text-slate-900">Simple, transparent pricing for every healthcare entity</h1>
        <p className="mt-3 text-slate-500">Start free. Scale as you grow.</p>
      </section>
      <section className="px-6 pb-20">
        <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
          {plans.map((plan, index) => (
            <article key={plan[0]} className={`rounded-2xl border bg-white p-6 shadow-sm ${index === 1 ? 'border-2 border-[#2563EB] shadow-2xl shadow-blue-900/10' : 'border-slate-100'}`}>
              <h2 className="font-semibold text-slate-900">{plan[0]}</h2>
              <p className="font-display mt-4 text-5xl text-slate-900">{plan[1]}</p>
              <p className="mt-4 text-sm leading-7 text-slate-600">{plan[2]}</p>
              <Link href="/signup" className={`mt-6 inline-flex w-full justify-center rounded-xl px-4 py-3 text-sm font-semibold ${index === 2 ? 'bg-slate-900 text-white' : 'bg-[#2563EB] text-white'}`}>Get Started</Link>
            </article>
          ))}
        </div>
        <div className="mx-auto mt-10 max-w-4xl overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
          {['AI Symptom Triage', 'Pidgin Support', 'Live Queue Tracking', 'NDPA Audit Logging', 'Multi-Entity Network', 'API Access'].map((feature, index) => (
            <div key={feature} className={`grid grid-cols-4 gap-3 px-4 py-3 text-sm ${index % 2 ? 'bg-white' : 'bg-slate-50/60'}`}>
              <span className="font-semibold text-slate-700">{feature}</span>
              <CheckCircle2 className="h-5 w-5 text-[#2563EB]" />
              <CheckCircle2 className="h-5 w-5 text-[#2563EB]" />
              <CheckCircle2 className="h-5 w-5 text-[#2563EB]" />
            </div>
          ))}
        </div>
      </section>
      <Footer />
    </main>
  );
}

