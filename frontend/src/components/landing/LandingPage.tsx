'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, Brain, CalendarCheck, CheckCircle2, Clock, Mail, MapPin, MessageSquare, Shield, Smartphone, Star, Users, Zap } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { conditionRows } from '@/lib/dashboard-data';

const headlines = [
  ['Your Health,', 'Understood', 'Instantly.'],
  ['The Right Doctor.', 'The Right Clinic.', 'Right Now.'],
  ['AI Triage Built', 'for Nigeria', 'Starting in Akwa Ibom.'],
];

const features = [
  ['AI Triage in 30 Seconds', 'Describe your symptoms in English or Pidgin. Our AI maps 200+ Nigerian disease conditions to the right specialist.', Zap],
  ['Nearest Clinic, Every Time', 'Route to the closest available specialist using real-time location and urgency-aware logic.', MapPin],
  ['100% Private & Compliant', 'NDPA 2023 compliance with audit logging, patient consent controls, and no localStorage token storage.', Shield],
  ['Appointment Confirmed', 'Get the specialist, clinic location, ticket number, and time slot before leaving the page.', CalendarCheck],
  ['Works on Any Device', 'Web, WhatsApp, and SMS-ready workflows keep care accessible even with limited internet.', Smartphone],
  ['Built for Every Entity', 'Patients, doctors, hospitals, clinics, pharmacies, labs, nurses, and HMOs share one coordinated network.', Users],
] as const;

const faqs = [
  ['What is SynaptiVerse?', 'SynaptiVerse is an AI-powered healthcare coordination platform built for Nigeria. It helps patients understand symptoms, route to the right specialist, and book care fast.'],
  ['How does AI triage work?', 'You describe symptoms in plain English or Pidgin. The AI uses a Nigerian medical knowledge graph to classify urgency and match the right specialist.'],
  ['Is my health information private?', 'Yes. Tokens are stored in HttpOnly cookies, and sensitive actions are protected with audit logs and NDPA-focused controls.'],
  ['How much does it cost for patients?', 'Patient signup is free, and the first AI triage flow is designed to be free at launch.'],
];

function Hero() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setCurrent((value) => (value + 1) % headlines.length), 3500);
    return () => window.clearInterval(timer);
  }, []);

  const headline = headlines[current];

  return (
    <section className="relative min-h-screen overflow-hidden bg-[#17173b] px-6 pb-20 pt-32 text-center text-white">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_20%,rgba(97,87,245,0.28)_0%,transparent_60%)]" />
      <div className="relative mx-auto max-w-5xl">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-800 bg-indigo-950 px-3 py-1.5 text-xs font-semibold text-indigo-300">
          Built for Nigeria - Powered by Claude AI
        </div>
        <h1 className="font-display text-5xl leading-tight md:text-7xl">
          {headline[0]}<br />
          {headline[1]}<br />
          <span className="text-[#8f8cff]">{headline[2]}</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-400">
          AI-powered symptom triage that tells you what might be wrong, how urgent it is, and gets you to the nearest right specialist in under 30 seconds.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Link href="/signup" className="inline-flex items-center gap-2 rounded-xl bg-[#6157f5] px-8 py-4 font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:-translate-y-0.5 hover:bg-[#4f46e5]">
            Sign Up For Free
            <ArrowRight className="h-5 w-5" />
          </Link>
          <Link href="/book-demo" className="rounded-xl border border-white/15 bg-white/5 px-8 py-4 font-semibold text-white transition hover:bg-white/10">Book a Demo</Link>
        </div>
        <div className="mt-8 flex flex-wrap justify-center gap-6 text-xs text-slate-500">
          {['NDPA 2023 Compliant', 'HttpOnly Cookies', '200+ Conditions', '30-Second Results'].map((item) => (
            <span key={item} className="inline-flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-indigo-300" />{item}</span>
          ))}
        </div>
        <div className="mx-auto mt-14 max-w-lg overflow-hidden rounded-2xl border border-slate-700/50 bg-slate-900 text-left shadow-2xl">
          <div className="flex items-center justify-between bg-slate-800 px-4 py-3">
            <span className="inline-flex items-center gap-2 text-sm font-semibold"><span className="h-2 w-2 animate-pulse rounded-full bg-indigo-300" />SynaptiVerse AI</span>
            <span className="rounded-full border border-indigo-800 bg-indigo-950 px-2 py-0.5 text-xs text-indigo-300">LIVE</span>
          </div>
          <div className="space-y-3 p-4">
            <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-[#6157f5] px-4 py-2.5 text-sm text-white">I have bad chest pain and cannot breathe well</div>
            <div className="max-w-[85%] rounded-2xl border border-slate-700 bg-slate-800 p-3 text-sm text-slate-300"><span className="rounded-full border border-rose-800 bg-rose-950 px-2 py-0.5 text-xs text-rose-400">URGENT</span><p className="mt-2">This needs a cardiologist review. Routing you now.</p></div>
            <div className="max-w-[85%] rounded-2xl border border-indigo-800/50 bg-slate-800 p-3 text-sm"><p className="font-semibold text-white">Appointment Confirmed</p><p className="text-xs text-slate-400">Dr. Effiong Bassey - Ibom Specialist Hospital - Today 3:00 PM</p></div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stats() {
  return (
    <section className="border-y border-slate-100 bg-white px-6 py-10">
      <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 text-center md:grid-cols-4">
        {[
          ['200+', 'Medical Conditions Mapped'],
          ['30s', 'Average Triage Response'],
          ['8', 'Entity Types Supported'],
          ['100%', 'NDPA 2023 Compliant'],
        ].map((stat) => (
          <div key={stat[1]}>
            <p className="font-display text-4xl text-slate-900">{stat[0]}</p>
            <p className="mt-1 text-sm text-slate-500">{stat[1]}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Conditions() {
  return (
    <section className="overflow-hidden bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-5xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">What We Cover</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Consult the right specialist for any health concern</h2>
        <p className="mx-auto mt-3 max-w-2xl text-slate-500">Our AI maps 200+ conditions to the right specialist, so you reach the right doctor first time.</p>
      </div>
      <div className="mt-10 grid gap-4">
        {conditionRows.map((row, index) => (
          <div key={index} className="overflow-hidden">
            <div className={`flex w-max gap-3 hover:[animation-play-state:paused] ${index === 0 ? 'animate-scroll-left' : 'animate-scroll-right'}`}>
              {[...row, ...row].map((chip, chipIndex) => (
                <Link key={`${chip}-${chipIndex}`} href={`/chat?symptom=${encodeURIComponent(chip.toLowerCase())}`} className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm transition hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700">
                  <span className={`mr-2 inline-block h-2 w-2 rounded-full ${index === 0 ? 'bg-rose-400' : 'bg-indigo-400'}`} />
                  {chip}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FeatureGrid() {
  return (
    <section className="bg-white px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">Why Choose Us</p>
          <h2 className="font-display mt-2 text-4xl text-slate-900">Everything you need. Nothing you do not.</h2>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {features.map(([title, body, Icon]) => (
            <article key={String(title)} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition hover:border-slate-200 hover:shadow-md">
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-indigo-50 text-[#6157f5]"><Icon className="h-6 w-6" /></div>
              <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    ['01', 'Describe Your Symptoms', 'Type how you feel in English, Pidgin, or both.', MessageSquare],
    ['02', 'AI Analyzes & Routes', 'Claude plus a Nigerian knowledge graph maps urgency and specialty.', Brain],
    ['03', 'Appointment Confirmed', 'You receive slot, doctor, clinic location, and ticket number.', CalendarCheck],
  ] as const;
  return (
    <section className="bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">How It Works</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">From symptom to specialist in 3 simple steps</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {steps.map(([num, title, body, Icon]) => (
            <article key={String(title)} className="rounded-2xl border border-slate-100 bg-white p-6 text-left shadow-sm">
              <p className="font-display text-5xl text-indigo-100">{num}</p>
              <div className="mt-2 grid h-12 w-12 place-items-center rounded-full bg-[#6157f5] text-white"><Icon className="h-6 w-6" /></div>
              <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
              <p className="mt-4 inline-flex items-center gap-1 text-xs text-slate-400"><Clock className="h-3 w-3" />Takes about 30 seconds</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function PricingPreview() {
  return (
    <section className="bg-slate-50 px-6 py-20" id="pricing">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">Pricing</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Simple pricing for every healthcare entity</h2>
        <div className="mt-10 grid gap-5 text-left md:grid-cols-3">
          {[
            ['Patient', '₦0', 'Always free for patients', 'AI symptom triage, clinic finder, queue tracking, health card'],
            ['Clinic / Specialist', '₦25,000', 'For small clinics and doctors', 'Dashboard, calendar, staff accounts, Kanban, analytics, audit logging'],
            ['Hospital / Enterprise', 'Custom', 'For hospitals, HMOs, labs', 'Unlimited staff, multi-tenant, API access, SLA, custom onboarding'],
          ].map((plan, index) => (
            <article key={plan[0]} className={`relative rounded-2xl border bg-white p-6 shadow-sm ${index === 1 ? 'scale-[1.02] border-2 border-[#6157f5] shadow-2xl shadow-indigo-900/10' : 'border-slate-100'}`}>
              {index === 0 ? <span className="absolute right-4 top-4 rounded-full bg-[#6157f5] px-3 py-1 text-xs font-semibold text-white">Most Popular</span> : null}
              <h3 className="font-semibold text-slate-900">{plan[0]}</h3>
              <p className="font-display mt-4 text-5xl text-slate-900">{plan[1]}</p>
              <p className="mt-2 text-sm text-slate-500">{plan[2]}</p>
              <p className="mt-6 text-sm leading-7 text-slate-600">{plan[3]}</p>
              <Link href="/signup" className={`mt-6 inline-flex w-full justify-center rounded-xl px-4 py-3 text-sm font-semibold ${index === 2 ? 'bg-slate-900 text-white' : 'bg-[#6157f5] text-white'}`}>Get Started</Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Testimonials() {
  const cards = [
    ['FE', 'Fatima Ekwueme', 'Patient, Uyo', 'The AI understood my symptoms and routed me to the right department without wasted trips.'],
    ['DO', 'Dr. Obiora Nwosu', 'Cardiologist, Nnewi', 'I receive pre-triaged patients now. Consultation time has dropped significantly.'],
    ['AC', 'Adaeze Chukwu', 'Clinic Manager, Lagos', 'The queue board replaced three spreadsheets. Our nurses love it.'],
  ];
  return (
    <section className="bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">What People Say</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Trusted by patients and clinics across Nigeria</h2>
        <div className="mt-4 flex justify-center gap-1 text-amber-400">{Array.from({ length: 5 }).map((_, i) => <Star key={i} className="h-4 w-4 fill-current" />)}</div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {cards.map((card) => (
            <article key={card[0]} className="rounded-2xl border border-slate-100 bg-white p-6 text-left shadow-sm">
              <p className="text-sm leading-6 text-slate-600">"{card[3]}"</p>
              <div className="mt-5 flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-[#8f8cff] to-[#4f46e5] text-sm font-bold text-white">{card[0]}</div>
                <div><p className="text-sm font-semibold text-slate-900">{card[1]}</p><p className="text-xs text-slate-400">{card[2]}</p></div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function FAQ() {
  const [open, setOpen] = useState(0);
  return (
    <section className="bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">FAQs</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Common questions, honest answers</h2>
      </div>
      <div className="mx-auto mt-10 max-w-2xl">
        {faqs.map((faq, index) => (
          <div key={faq[0]} className="mb-3 overflow-hidden rounded-xl border border-slate-200 bg-white">
            <button onClick={() => setOpen(open === index ? -1 : index)} className="flex w-full justify-between px-5 py-4 text-left text-sm font-semibold text-slate-900">{faq[0]}<span>{open === index ? '-' : '+'}</span></button>
            {open === index ? <p className="border-t border-slate-100 px-5 pb-4 pt-3 text-sm leading-6 text-slate-500">{faq[1]}</p> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function Newsletter() {
  const [subscribed, setSubscribed] = useState(false);
  return (
    <section className="border-t border-slate-100 bg-white px-6 py-16 text-center">
      <div className="mx-auto max-w-lg">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-indigo-50 text-[#6157f5]"><Mail className="h-6 w-6" /></div>
        <h3 className="font-display mt-4 text-3xl text-slate-900">Get health insights delivered to your inbox</h3>
        <p className="mt-2 text-sm text-slate-500">Weekly tips, disease alerts relevant to Nigeria, and platform updates.</p>
        {subscribed ? (
          <p className="mt-6 text-sm font-semibold text-[#6157f5]">Subscribed. Check your inbox for a welcome message.</p>
        ) : (
          <form onSubmit={(event) => { event.preventDefault(); setSubscribed(true); }} className="mt-6 flex gap-2">
            <input type="email" required placeholder="your@email.com" className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
            <button className="rounded-xl bg-[#6157f5] px-5 py-3 text-sm font-semibold text-white">Subscribe</button>
          </form>
        )}
      </div>
    </section>
  );
}

export function LandingPage() {
  return (
    <main>
      <Navbar />
      <Hero />
      <Stats />
      <Conditions />
      <FeatureGrid />
      <HowItWorks />
      <section className="bg-[#6157f5] px-6 py-16 text-white">
        <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-2 md:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-100">For Doctors & Specialists</p>
            <h2 className="font-display mt-2 text-4xl">Join healthcare professionals on SynaptiVerse</h2>
            <p className="mt-3 text-indigo-100">Receive AI-matched patient referrals, manage your schedule, and see patient history before consultation.</p>
          </div>
          <Link href="/specialists" className="w-fit rounded-xl bg-white px-6 py-3.5 font-semibold text-[#6157f5]">Join as a Specialist</Link>
        </div>
      </section>
      <PricingPreview />
      <Testimonials />
      <FAQ />
      <Newsletter />
      <Footer />
    </main>
  );
}
