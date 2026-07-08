import Link from 'next/link';
import { Clock, FileText, Target, User, Wallet, Building2, Stethoscope, CheckCircle2 } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

const offers = [
  ['AI-Matched Patients', 'Receive patients already triaged and matched to your specialty by our AI.', Target],
  ['Flexible Schedule', 'Set availability, block time, and manage appointments from one dashboard.', Clock],
  ['Instant Patient History', 'See symptoms, AI triage result, urgency, and ticket history before consultation.', FileText],
  ['Automated Payments', 'Consultation fees are collected and disbursed automatically.', Wallet],
] as const;

export default function SpecialistsPage() {
  return (
    <main className="bg-slate-50">
      <Navbar />
      <section className="bg-[#0D1117] px-6 pb-20 pt-32 text-white">
        <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-[1fr_0.6fr] md:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-300">For Doctors & Specialists</p>
            <h1 className="font-display mt-4 text-5xl leading-tight md:text-7xl">Expand your practice. Reach more patients. Earn more.</h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-400">Join SynaptiVerse's growing network of specialists. Our AI triage engine sends you correctly routed patients so you spend less time on admin and more time on care.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/signup?type=specialist" className="rounded-xl bg-[#2563EB] px-6 py-3.5 font-semibold text-white">Register as a Specialist</Link>
              <Link href="/specialist/login" className="rounded-xl border border-white/15 px-6 py-3.5 font-semibold text-white">Already registered? Sign in</Link>
            </div>
          </div>
          <div className="rounded-2xl bg-white p-5 text-slate-700 shadow-xl">
            <p className="text-sm font-semibold">12 new patients matched this week</p>
            <p className="mt-2 text-xs text-slate-400">Live referrals from AI triage are ready for verified specialists.</p>
          </div>
        </div>
      </section>
      <section className="px-6 py-20">
        <div className="mx-auto grid max-w-6xl gap-4 md:grid-cols-2 xl:grid-cols-4">
          {offers.map(([title, body, Icon]) => (
            <article key={String(title)} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <Icon className="h-7 w-7 text-[#2563EB]" />
              <h2 className="mt-4 font-semibold text-slate-900">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-display text-center text-4xl text-slate-900">How to join</h2>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {([
              ['Register Independently', 'Set up your own practice on SynaptiVerse with your schedule and fees.', User],
              ['Join Under a Facility', 'Connect to a partner hospital or clinic for shared records and scheduling.', Building2],
              ['Register Your Clinic', 'Own a private practice? Register it and add yourself as primary specialist.', Stethoscope],
            ] as const).map(([title, body, Icon]) => (
              <article key={String(title)} className="rounded-2xl border border-slate-100 bg-slate-50 p-6">
                <Icon className="h-6 w-6 text-[#2563EB]" />
                <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
              </article>
            ))}
          </div>
          <div className="mt-10 rounded-2xl border border-slate-100 bg-slate-50 p-6">
            <h3 className="font-semibold text-slate-900">To register, you will need:</h3>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {['Valid MDCN license', 'Practicing certificate', 'Government-issued ID', 'Bank account for disbursement', 'Device with camera for teleconsultation'].map((item) => (
                <p key={item} className="inline-flex items-center gap-2 text-sm text-slate-600"><CheckCircle2 className="h-4 w-4 text-[#2563EB]" />{item}</p>
              ))}
            </div>
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
