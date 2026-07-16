'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, BrainCircuit, Building2, CalendarCheck, Check, ChevronRight, Clock3, HeartPulse, MapPin, MessageCircle, ShieldCheck, Sparkles, Stethoscope, Users } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { api } from '@/lib/auth';

type PlatformStats = Record<string, number>;

const symptomExamples = [
  { text: 'I have had a high fever and feel very weak for two days', urgency: 'URGENT', route: 'General Medicine', time: 'See a clinician today' },
  { text: 'Sudden chest pain and difficulty breathing', urgency: 'CRITICAL', route: 'Emergency Medicine', time: 'Seek emergency care now' },
  { text: 'Mild itchy rash on my arm since yesterday', urgency: 'ROUTINE', route: 'Dermatology', time: 'Book the next available visit' },
];

type PreviewResult = { urgency: string; specialty: string; recommended_timing: string; condition_name?: string; disclaimer?: string };

const faqs = [
  ['Is the symptom analysis a diagnosis?', 'No. It identifies possible urgency and the most appropriate care route. A qualified clinician must make the diagnosis.'],
  ['What happens after I describe my symptoms?', 'Authenticated patients receive an urgency result, specialty route, clinic suggestion, available appointment, and a trackable visit ticket.'],
  ['Can I use English or Pidgin?', 'Yes. The intake accepts natural symptom descriptions, including common Nigerian English and Pidgin expressions.'],
  ['Who can access my health information?', 'Only authenticated, authorized roles within your care workflow. Access and sensitive actions are recorded for auditability.'],
  ['Can hospitals and clinics use the same platform?', 'Yes. Hospitals, clinics, specialists, nurses, laboratories, pharmacies, HMOs, and public-health teams have role-specific workspaces.'],
];

const portals = [
  ['Patients', 'AI triage, queue tracking and appointments', HeartPulse],
  ['Care teams', 'One shared clinical queue with safe handoffs', Stethoscope],
  ['Facilities', 'Capacity, scheduling and operational visibility', Building2],
  ['Health networks', 'Claims, referrals and population insights', Users],
] as const;

function SymptomPreview() {
  const [index, setIndex] = useState(0);
  const [text, setText] = useState(symptomExamples[0].text);
  const [result, setResult] = useState<PreviewResult>({ urgency: symptomExamples[0].urgency, specialty: symptomExamples[0].route, recommended_timing: symptomExamples[0].time });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function analyze() {
    if (text.trim().length < 3) { setError('Describe your symptoms in a little more detail.'); return; }
    setLoading(true);
    setError('');
    try {
      const payload = await api.post('/api/v1/public/triage-preview', { symptom_description: text.trim() }) as PreviewResult;
      setResult(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to analyze symptoms right now.');
    } finally { setLoading(false); }
  }

  function nextExample() {
    const next = (index + 1) % symptomExamples.length;
    const example = symptomExamples[next];
    setIndex(next); setText(example.text); setResult({ urgency: example.urgency, specialty: example.route, recommended_timing: example.time }); setError('');
  }

  const critical = result.urgency === 'CRITICAL';
  return (
    <div className="relative rounded-[2rem] border border-white/10 bg-white/10 p-3 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-4">
      <div className="rounded-[1.5rem] bg-[#f7f7f1] p-5 text-[#10231e] sm:p-7">
        <div className="flex items-center justify-between gap-4">
          <div><p className="sv-kicker">Live product preview</p><h2 className="mt-1 text-xl font-black">What are you feeling?</h2></div>
          <span className="grid h-11 w-11 place-items-center rounded-full bg-[#d8ee72]"><BrainCircuit className="h-5 w-5" /></span>
        </div>
        <textarea aria-label="Try a symptom description" value={text} onChange={(event) => setText(event.target.value)} rows={4} className="mt-5 w-full resize-none rounded-2xl border border-[#dbe2dc] bg-white p-4 text-sm leading-6 outline-none focus:border-[#0b5d4b]" />
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" disabled={loading} onClick={() => void analyze()} className="sv-button-dark flex-1">{loading ? 'Analyzing…' : 'Analyze symptoms'}<Sparkles className="h-4 w-4" /></button>
          <button type="button" onClick={nextExample} className="min-h-12 rounded-full border border-[#dbe2dc] px-4 text-sm font-bold">Try example</button>
        </div>
        <div aria-live="polite" className="mt-5 rounded-2xl border border-[#dbe2dc] bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3"><span className={`rounded-full px-3 py-1 text-xs font-black ${critical ? 'bg-rose-100 text-rose-700' : result.urgency === 'URGENT' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-700'}`}>{result.urgency}</span><span className="text-xs font-semibold text-[#60706a]">Illustrative preview</span></div>
          {result.condition_name ? <p className="mt-4 text-sm text-[#60706a]">Possible pattern: <b className="text-[#10231e]">{result.condition_name}</b></p> : null}
          <div className="mt-4 grid gap-3 sm:grid-cols-2"><div><p className="text-xs font-bold uppercase tracking-wider text-[#60706a]">Suggested care route</p><p className="mt-1 font-black">{result.specialty}</p></div><div><p className="text-xs font-bold uppercase tracking-wider text-[#60706a]">Recommended timing</p><p className="mt-1 font-black">{result.recommended_timing}</p></div></div>
          {result.disclaimer ? <p className="mt-4 border-t border-[#dbe2dc] pt-3 text-xs leading-5 text-[#60706a]">{result.disclaimer}</p> : null}
        </div>
        {error ? <p role="alert" className="mt-3 rounded-xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">{error}</p> : null}
        <Link href="/login" className="mt-4 inline-flex items-center gap-2 text-sm font-black text-[#0b5d4b]">Sign in for clinical triage and booking <ArrowRight className="h-4 w-4" /></Link>
      </div>
    </div>
  );
}

export function ModernLandingPage() {
  const [stats, setStats] = useState<PlatformStats>({});
  useEffect(() => { api.get('/api/v1/public/platform-stats').then((value) => setStats((value ?? {}) as PlatformStats)).catch(() => undefined); }, []);
  const statItems = [
    ['Care entities', stats.care_entities ?? 10, 'connected roles'],
    ['Channels', stats.channels ?? 3, 'web, SMS, WhatsApp'],
    ['Always on', '24/7', 'intake and routing'],
  ];

  return (
    <main className="overflow-hidden bg-[#f4f5ef] text-[#10231e]">
      <Navbar />
      <section className="relative bg-[#073d33] pb-20 pt-32 text-white lg:pb-28 lg:pt-40">
        <div className="absolute inset-0 opacity-40 [background-image:radial-gradient(circle_at_10%_10%,rgba(216,238,114,.22),transparent_30%),radial-gradient(circle_at_90%_80%,rgba(213,170,85,.18),transparent_30%)]" />
        <div className="sv-container relative grid gap-14 lg:grid-cols-[1.02fr_.98fr] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#d8ee72]"><span className="h-2 w-2 rounded-full bg-[#d8ee72]" />Care intelligence for Nigeria</div>
            <h1 className="mt-7 max-w-4xl font-display text-5xl leading-[.98] tracking-[-0.04em] sm:text-6xl lg:text-[5.4rem]">From symptoms to the <span className="text-[#d8ee72]">right care</span>, without the guesswork.</h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-white/70">ClinicalFlow understands what patients feel, identifies urgency, and coordinates the next best clinical action across the entire care network.</p>
            <div className="mt-9 flex flex-wrap gap-3"><Link href="/signup?type=patient" className="sv-button-primary">Start as a patient <ArrowRight className="h-4 w-4" /></Link><Link href="/book-demo" className="inline-flex min-h-12 items-center justify-center rounded-full border border-white/20 px-6 py-3 text-sm font-bold hover:bg-white/10">Book a platform demo</Link></div>
            <div className="mt-9 flex flex-wrap gap-x-6 gap-y-3 text-sm text-white/60">{['Consent-first', 'Secure sessions', 'Auditable handoffs'].map((item) => <span key={item} className="inline-flex items-center gap-2"><Check className="h-4 w-4 text-[#d8ee72]" />{item}</span>)}</div>
          </div>
          <SymptomPreview />
        </div>
      </section>

      <section className="border-b border-[#dbe2dc] bg-white"><div className="sv-container grid divide-y divide-[#dbe2dc] md:grid-cols-3 md:divide-x md:divide-y-0">{statItems.map(([value, metric, copy]) => <div key={String(value)} className="px-4 py-8 text-center"><p className="font-display text-4xl text-[#073d33]">{metric}</p><p className="mt-1 text-sm text-[#60706a]">{copy}</p></div>)}</div></section>

      <section className="sv-container py-24 lg:py-32">
        <div className="grid gap-12 lg:grid-cols-[.8fr_1.2fr] lg:items-end"><div><p className="sv-kicker">One connected health system</p><h2 className="mt-4 font-display text-4xl leading-tight sm:text-6xl">Every handoff becomes visible.</h2></div><p className="max-w-2xl text-lg leading-8 text-[#60706a]">A patient should never have to restart their story at every doorway. ClinicalFlow gives each authorized care team the right context at the right moment.</p></div>
        <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-4">{portals.map(([title, body, Icon], index) => <article key={title} className={`rounded-[1.75rem] p-7 ${index === 0 ? 'bg-[#073d33] text-white' : 'border border-[#dbe2dc] bg-white'}`}><span className={`grid h-12 w-12 place-items-center rounded-full ${index === 0 ? 'bg-[#d8ee72] text-[#073d33]' : 'bg-[#e9f6f1] text-[#0b5d4b]'}`}><Icon className="h-5 w-5" /></span><h3 className="mt-10 text-xl font-black">{title}</h3><p className={`mt-3 text-sm leading-6 ${index === 0 ? 'text-white/65' : 'text-[#60706a]'}`}>{body}</p><ChevronRight className="mt-7 h-5 w-5" /></article>)}</div>
      </section>

      <section className="bg-[#e8eadf] py-24"><div className="sv-container"><div className="mx-auto max-w-3xl text-center"><p className="sv-kicker">How care moves</p><h2 className="mt-4 font-display text-4xl sm:text-6xl">One calm journey from concern to care.</h2></div><div className="mt-14 grid gap-4 lg:grid-cols-3">{[[MessageCircle,'Tell us what is happening','Use natural language—English, Pidgin, or the words that feel easiest.'],[BrainCircuit,'Understand risk and specialty','Clinical routing logic maps urgency, specialty, and the appropriate next action.'],[CalendarCheck,'Continue into coordinated care','Book a verified slot, track the queue, and carry context into the consultation.']].map(([Icon,title,body],index) => { const StepIcon = Icon as typeof MessageCircle; return <article key={String(title)} className="sv-panel p-7"><p className="text-sm font-black text-[#d5aa55]">0{index+1}</p><StepIcon className="mt-12 h-8 w-8 text-[#0b5d4b]"/><h3 className="mt-6 text-xl font-black">{String(title)}</h3><p className="mt-3 text-sm leading-7 text-[#60706a]">{String(body)}</p></article>; })}</div></div></section>

      <section className="sv-container py-24"><div className="grid overflow-hidden rounded-[2.5rem] bg-[#073d33] text-white lg:grid-cols-2"><div className="p-8 sm:p-12 lg:p-16"><ShieldCheck className="h-10 w-10 text-[#d8ee72]"/><h2 className="mt-8 font-display text-4xl sm:text-5xl">Clinical context, protected by design.</h2><p className="mt-6 max-w-xl leading-8 text-white/65">Role-aware access, consent controls, audit-ready events, secure sessions, and tenant isolation are built into the platform—not added as an afterthought.</p><Link href="/privacy" className="mt-8 inline-flex items-center gap-2 font-bold text-[#d8ee72]">Explore privacy and security <ArrowRight className="h-4 w-4"/></Link></div><div className="grid content-center gap-4 bg-white/5 p-8 sm:p-12">{[[Clock3,'Live queue visibility'],[MapPin,'Location-aware routing'],[ShieldCheck,'Consent-first records']].map(([Icon,label])=>{const ItemIcon=Icon as typeof Clock3;return <div key={String(label)} className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-5"><span className="grid h-11 w-11 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><ItemIcon className="h-5 w-5"/></span><span className="font-bold">{String(label)}</span></div>;})}</div></div></section>

      <section className="bg-white py-24"><div className="sv-container grid gap-12 lg:grid-cols-[.7fr_1.3fr]"><div><p className="sv-kicker">Frequently asked questions</p><h2 className="mt-4 font-display text-4xl leading-tight sm:text-5xl">Clear answers before you begin.</h2><p className="mt-5 leading-7 text-[#60706a]">Still need help? Contact the team through the demo request page.</p><Link href="/book-demo" className="mt-6 inline-flex items-center gap-2 font-black text-[#0b5d4b]">Talk to our team <ArrowRight className="h-4 w-4" /></Link></div><div className="divide-y divide-[#dbe2dc] border-y border-[#dbe2dc]">{faqs.map(([question,answer]) => <details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-black text-[#10231e]">{question}<span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#e9f6f1] text-[#0b5d4b] transition group-open:rotate-45">+</span></summary><p className="max-w-2xl pt-4 leading-7 text-[#60706a]">{answer}</p></details>)}</div></div></section>

      <section className="px-5 pb-24"><div className="sv-container rounded-[2.5rem] bg-[#d8ee72] px-7 py-16 text-center sm:px-12"><p className="sv-kicker">Ready when you are</p><h2 className="mx-auto mt-4 max-w-3xl font-display text-4xl leading-tight text-[#073d33] sm:text-6xl">Start with the symptom. We’ll help coordinate what comes next.</h2><div className="mt-8 flex flex-wrap justify-center gap-3"><Link href="/signup?type=patient" className="sv-button-dark">Create patient account</Link><Link href="/login" className="inline-flex min-h-12 items-center rounded-full border border-[#073d33]/20 px-6 text-sm font-bold text-[#073d33]">I already have an account</Link></div></div></section>
      <Footer />
    </main>
  );
}
