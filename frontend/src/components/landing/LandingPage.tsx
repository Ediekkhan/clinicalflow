'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, Brain, CalendarCheck, CheckCircle2, Mail, MapPin, MessageSquare, Shield, Smartphone, Users, Zap } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { api } from '@/lib/auth';

type PlatformStats = Record<string, number>;
type PublicPlan = { id?: string; name?: string; price_label?: string; description?: string; cta_href?: string };
type PublicArticle = { id?: string; title?: string; category?: string; excerpt?: string };
type Testimonial = { id?: string; initials?: string; name?: string; role?: string; quote?: string };

const headlines = [
  ['Your Health,', 'Understood', 'Instantly.'],
  ['The Right Doctor.', 'The Right Clinic.', 'Right Now.'],
  ['AI Triage Built', 'for Nigeria', 'Starting in Akwa Ibom.'],
];

const features = [
  ['AI Triage', 'Describe symptoms in natural language and route to the right care path.', Zap],
  ['Nearest Clinic', 'Match patients with available care teams using location-aware workflows.', MapPin],
  ['Private by Design', 'Consent controls, audit logging, and secure cookie sessions protect patient data.', Shield],
  ['Appointment Confirmation', 'Show the selected specialist, facility, ticket, and slot from live API responses.', CalendarCheck],
  ['Works on Any Device', 'Web, WhatsApp, and SMS-ready workflows keep care accessible.', Smartphone],
  ['Built for Every Entity', 'Patients, doctors, hospitals, clinics, pharmacies, labs, nurses, and HMOs share one network.', Users],
] as const;

const faqs = [
  ['What is SynaptiVerse?', 'SynaptiVerse is an AI-powered healthcare coordination platform built for Nigeria.'],
  ['How does AI triage work?', 'Patients describe symptoms, then the platform routes them based on urgency, location, and specialty.'],
  ['Is health information private?', 'Yes. Sensitive actions are protected with secure sessions, consent controls, and audit logs.'],
  ['How do I get started?', 'Create an account, complete verification where required, and connect to your care workflow.'],
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
      <div className="relative mx-auto max-w-5xl">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-800 bg-indigo-950 px-3 py-1.5 text-xs font-semibold text-indigo-300">
          Built for Nigeria
        </div>
        <h1 className="font-display text-5xl leading-tight md:text-7xl">
          {headline[0]}<br />
          {headline[1]}<br />
          <span className="text-[#8f8cff]">{headline[2]}</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-400">
          AI-powered symptom triage that explains urgency and connects patients to the right available care team.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Link href="/signup" className="inline-flex items-center gap-2 rounded-xl bg-[#6157f5] px-8 py-4 font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:-translate-y-0.5 hover:bg-[#4f46e5]">
            Sign Up
            <ArrowRight className="h-5 w-5" />
          </Link>
          <Link href="/book-demo" className="rounded-xl border border-white/15 bg-white/5 px-8 py-4 font-semibold text-white transition hover:bg-white/10">Book a Demo</Link>
        </div>
        <div className="mt-8 flex flex-wrap justify-center gap-6 text-xs text-slate-500">
          {['NDPA Compliant', 'HttpOnly Cookies', 'Consent Controls', 'Audit Logging'].map((item) => (
            <span key={item} className="inline-flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-indigo-300" />{item}</span>
          ))}
        </div>
        <div className="mx-auto mt-14 max-w-lg overflow-hidden rounded-2xl border border-slate-700/50 bg-slate-900 text-left shadow-2xl">
          <div className="flex items-center justify-between bg-slate-800 px-4 py-3">
            <span className="inline-flex items-center gap-2 text-sm font-semibold"><span className="h-2 w-2 animate-pulse rounded-full bg-indigo-300" />SynaptiVerse AI</span>
            <span className="rounded-full border border-indigo-800 bg-indigo-950 px-2 py-0.5 text-xs text-indigo-300">LIVE</span>
          </div>
          <div className="space-y-3 p-4">
            <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-[#6157f5] px-4 py-2.5 text-sm text-white">I need help deciding where to go for care</div>
            <div className="max-w-[85%] rounded-2xl border border-slate-700 bg-slate-800 p-3 text-sm text-slate-300"><span className="rounded-full border border-amber-800 bg-amber-950 px-2 py-0.5 text-xs text-amber-400">TRIAGE</span><p className="mt-2">I can check urgency and route you to an available care team.</p></div>
            <div className="max-w-[85%] rounded-2xl border border-indigo-800/50 bg-slate-800 p-3 text-sm"><p className="font-semibold text-white">Appointment Confirmation</p><p className="text-xs text-slate-400">Live facility, provider, and slot details load from the API.</p></div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stats({ platformStats }: { platformStats: PlatformStats | null }) {
  if (!platformStats) return null;
  const entries = Object.entries(platformStats);
  if (!entries.length) return null;

  return (
    <section className="border-y border-slate-100 bg-white px-6 py-10">
      <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 text-center md:grid-cols-4">
        {entries.slice(0, 4).map(([label, value]) => (
          <div key={label}>
            <p className="font-display text-4xl text-slate-900">{value.toLocaleString()}</p>
            <p className="mt-1 text-sm capitalize text-slate-500">{label.replaceAll('_', ' ')}</p>
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
    ['Describe Your Symptoms', 'Type how you feel in English, Pidgin, or both.', MessageSquare],
    ['AI Analyzes and Routes', 'The platform maps urgency and specialty from live clinical logic.', Brain],
    ['Appointment Confirmed', 'You receive slot, provider, facility, and ticket details from the API.', CalendarCheck],
  ] as const;
  return (
    <section className="bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">How It Works</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">From symptom to specialist</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {steps.map(([title, body, Icon], index) => (
            <article key={String(title)} className="rounded-2xl border border-slate-100 bg-white p-6 text-left shadow-sm">
              <p className="font-display text-5xl text-indigo-100">{index + 1}</p>
              <div className="mt-2 grid h-12 w-12 place-items-center rounded-full bg-[#6157f5] text-white"><Icon className="h-6 w-6" /></div>
              <h3 className="mt-4 font-semibold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function PricingPreview({ plans }: { plans: PublicPlan[] }) {
  if (!plans.length) return null;
  return (
    <section className="bg-slate-50 px-6 py-20" id="pricing">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">Pricing</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Plans from the SynaptiVerse API</h2>
        <div className="mt-10 grid gap-5 text-left md:grid-cols-3">
          {plans.map((plan) => (
            <article key={plan.id ?? plan.name} className="relative rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <h3 className="font-semibold text-slate-900">{plan.name}</h3>
              <p className="font-display mt-4 text-5xl text-slate-900">{plan.price_label ?? '—'}</p>
              {plan.description ? <p className="mt-6 text-sm leading-7 text-slate-600">{plan.description}</p> : null}
              <Link href={plan.cta_href ?? '/signup'} className="mt-6 inline-flex w-full justify-center rounded-xl bg-[#6157f5] px-4 py-3 text-sm font-semibold text-white">Get Started</Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Articles({ posts }: { posts: PublicArticle[] }) {
  return (
    <section className="bg-white px-6 py-20">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">Articles</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Health updates</h2>
        {posts.length === 0 ? (
          <div className="py-16 text-center text-slate-400"><p>No articles published yet. Check back soon.</p></div>
        ) : (
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {posts.map((post) => (
              <article key={post.id ?? post.title} className="rounded-2xl border border-slate-100 bg-white p-6 text-left shadow-sm">
                {post.category ? <p className="text-xs font-semibold text-[#6157f5]">{post.category}</p> : null}
                <h3 className="mt-3 font-semibold text-slate-900">{post.title}</h3>
                {post.excerpt ? <p className="mt-2 text-sm leading-6 text-slate-500">{post.excerpt}</p> : null}
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Testimonials({ testimonials }: { testimonials: Testimonial[] }) {
  if (!testimonials.length) return null;
  return (
    <section className="bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-6xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6157f5]">What People Say</p>
        <h2 className="font-display mt-2 text-4xl text-slate-900">Trusted by care teams</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {testimonials.map((card) => (
            <article key={card.id ?? card.quote} className="rounded-2xl border border-slate-100 bg-white p-6 text-left shadow-sm">
              <p className="text-sm leading-6 text-slate-600">{card.quote}</p>
              <div className="mt-5 flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-[#8f8cff] to-[#4f46e5] text-sm font-bold text-white">{card.initials}</div>
                <div><p className="text-sm font-semibold text-slate-900">{card.name}</p><p className="text-xs text-slate-400">{card.role}</p></div>
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
        <h2 className="font-display mt-2 text-4xl text-slate-900">Common questions</h2>
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
        <h2 className="font-display mt-4 text-3xl text-slate-900">Stay updated</h2>
        <form onSubmit={(event) => { event.preventDefault(); setSubscribed(true); }} className="mt-6 flex gap-2">
          <input type="email" required placeholder="Email address" className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#6157f5]" />
          <button className="rounded-xl bg-[#6157f5] px-5 py-3 text-sm font-semibold text-white">Subscribe</button>
        </form>
        {subscribed ? <p className="mt-3 text-sm text-[#6157f5]">Thanks. You are on the list.</p> : null}
      </div>
    </section>
  );
}

export function LandingPage() {
  const [platformStats, setPlatformStats] = useState<PlatformStats | null>(null);
  const [plans, setPlans] = useState<PublicPlan[]>([]);
  const [posts, setPosts] = useState<PublicArticle[]>([]);
  const [testimonials, setTestimonials] = useState<Testimonial[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function loadPublicData() {
      try {
        const [statsResult, pricingResult, postsResult, testimonialsResult] = await Promise.allSettled([
          api.get('/api/v1/public/platform-stats'),
          api.get('/api/v1/public/pricing'),
          api.get('/api/v1/public/blog-posts'),
          api.get('/api/v1/public/testimonials'),
        ]);
        if (cancelled) return;
        setPlatformStats(statsResult.status === 'fulfilled' ? (statsResult.value as PlatformStats) : null);
        const pricing = pricingResult.status === 'fulfilled' ? (pricingResult.value as { plans?: PublicPlan[] }) : {};
        setPlans(Array.isArray(pricing.plans) ? pricing.plans : []);
        setPosts(postsResult.status === 'fulfilled' && Array.isArray(postsResult.value) ? (postsResult.value as PublicArticle[]) : []);
        setTestimonials(testimonialsResult.status === 'fulfilled' && Array.isArray(testimonialsResult.value) ? (testimonialsResult.value as Testimonial[]) : []);
      } catch (error) {
        console.error(error);
      }
    }
    void loadPublicData();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="bg-white text-slate-900">
      <Navbar />
      <Hero />
      <Stats platformStats={platformStats} />
      <FeatureGrid />
      <HowItWorks />
      <PricingPreview plans={plans} />
      <Articles posts={posts} />
      <Testimonials testimonials={testimonials} />
      <FAQ />
      <Newsletter />
      <Footer />
    </main>
  );
}
