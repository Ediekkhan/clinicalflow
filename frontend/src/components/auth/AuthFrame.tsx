import Link from 'next/link';
import { Activity, ArrowLeft, CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';

export function AuthFrame({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: ReactNode }) {
  return (
    <main className="min-h-screen bg-[#f4f5ef] p-2 sm:p-5">
      <div className="mx-auto grid min-h-[calc(100vh-1rem)] max-w-[1440px] overflow-hidden rounded-[1.25rem] bg-white shadow-[0_30px_100px_rgba(7,61,51,.12)] sm:rounded-[2rem] lg:min-h-[calc(100vh-2.5rem)] lg:grid-cols-[1.08fr_.92fr]">
        <section className="relative hidden overflow-hidden bg-[#073d33] p-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div className="absolute inset-0 opacity-60 [background-image:radial-gradient(circle_at_20%_15%,rgba(216,238,114,.2),transparent_28%),radial-gradient(circle_at_85%_85%,rgba(213,170,85,.18),transparent_30%)]" />
          <div className="relative"><Link href="/" className="inline-flex items-center gap-3 font-display text-2xl"><span className="grid h-10 w-10 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><Activity className="h-5 w-5" /></span>ClinicalFlow</Link></div>
          <div className="relative max-w-xl"><span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-[.18em] text-[#d8ee72]"><Sparkles className="h-4 w-4" />Care, clearly coordinated</span><h2 className="mt-7 font-display text-6xl leading-[1.02]">Your health story should move with you.</h2><p className="mt-6 max-w-lg text-lg leading-8 text-white/65">Understand symptoms, see urgency, find the right care team, and follow every next step from one calm workspace.</p></div>
          <div className="relative grid grid-cols-3 gap-3">{['Consent-first','Role protected','Audit ready'].map((item) => <div key={item} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm font-bold"><CheckCircle2 className="mb-3 h-5 w-5 text-[#d8ee72]" />{item}</div>)}</div>
        </section>
        <section className="flex min-h-full flex-col p-5 sm:p-10 lg:p-14 xl:p-20">
          <div className="flex items-center justify-between"><Link href="/" className="inline-flex items-center gap-2 text-sm font-bold text-[#60706a]"><ArrowLeft className="h-4 w-4" />Home</Link><span className="inline-flex items-center gap-2 text-xs font-bold text-[#0b5d4b]"><ShieldCheck className="h-4 w-4" />Secure access</span></div>
          <div className="my-auto py-8 sm:py-10"><p className="sv-kicker">{eyebrow}</p><h1 className="mt-4 max-w-xl break-words font-display text-3xl leading-tight text-[#10231e] sm:text-5xl">{title}</h1><p className="mt-4 max-w-lg leading-7 text-[#60706a]">{description}</p><div className="mt-8 sm:mt-9">{children}</div></div>
        </section>
      </div>
    </main>
  );
}
