import Link from 'next/link';
import { ArrowRight, BrainCircuit, Hospital, MapPin, MessageCircle } from 'lucide-react';

const featureCards = [
  { title: 'AI triage in context', body: 'English and Pidgin symptom capture with deterministic clinical graph routing.', icon: MessageCircle },
  { title: 'Nearby clinic matching', body: 'Urgency-aware routing across Akwa Ibom and Lagos partner clinics.', icon: MapPin },
  { title: 'Real-time specialist handoff', body: 'Specialists receive ticket notifications immediately without polling.', icon: Hospital },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#F7F8FA]">
      <header className="bg-[#0D1117] text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 p-4 md:p-6">
          <Link href="/" className="font-display text-3xl text-emerald-300">SynaptiVerse</Link>
          <nav className="flex items-center gap-2">
            <Link href="/signup" className="touch-target px-3 text-slate-200 hover:bg-white/10 sm:px-4">Get Started</Link>
            <Link href="/hospital/login" className="touch-target px-3 text-slate-200 hover:bg-white/10 sm:px-4">Hospital</Link>
          </nav>
        </div>
      </header>
      <section className="hero-radial text-white">
        <div className="mx-auto grid max-w-7xl gap-10 p-4 py-16 md:grid-cols-[1fr_0.9fr] md:p-6 md:py-24">
          <div className="grid content-center gap-8">
            <p className="text-sm font-bold uppercase tracking-wider text-emerald-300">Your AI Health Companion — Built for Nigeria</p>
            <h1 className="font-display max-w-3xl text-5xl leading-none tracking-tight md:text-8xl">
              Your Health. Understood. Instantly.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-slate-300">
              SynaptiVerse helps patients describe symptoms in English or Pidgin, finds the right nearby clinic, and keeps specialists notified in real time.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/signup" className="touch-target inline-flex items-center gap-2 bg-[#0D7A5F] text-white hover:bg-emerald-700">
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/chat" className="touch-target bg-white/10 text-white ring-1 ring-white/15 hover:bg-white/15">How It Works</Link>
            </div>
          </div>
          <div className="grid content-center">
            <div className="rounded-card border border-white/10 bg-white/8 p-4 shadow-md backdrop-blur">
              <div className="rounded-card bg-[#F7F8FA] p-4 text-[#111827]">
                <div className="flex items-center gap-3 border-b border-[#E5E7EB] pb-4">
                  <div className="grid h-10 w-10 place-items-center rounded-full bg-[#0D7A5F] text-white">
                    <BrainCircuit className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-bold">SynaptiVerse AI Triage</p>
                    <p className="text-sm text-[#6B7280]">● Live</p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3">
                  <div className="max-w-[85%] rounded-card bg-white p-3 text-sm shadow-sm">Describe what you are feeling in your own words.</div>
                  <div className="ml-auto max-w-[80%] rounded-card bg-[#0D7A5F] p-3 text-sm text-white">Body hot and head dey pain since yesterday.</div>
                  <div className="max-w-[90%] rounded-card border border-[#93C5FD] bg-[#EFF6FF] p-3 text-sm text-[#0284C7]">
                    ROUTINE · Malaria screening · Uyo Family Clinic, 2.4km away
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="mx-auto grid max-w-7xl gap-4 p-4 py-16 md:grid-cols-3 md:p-6">
        {featureCards.map((feature) => (
          <article key={feature.title} className="rounded-card border border-[#E5E7EB] bg-white p-6 shadow-sm">
            <feature.icon className="h-6 w-6 text-[#0D7A5F]" />
            <h2 className="mt-5 text-lg font-bold text-[#111827]">{feature.title}</h2>
            <p className="mt-2 text-sm leading-6 text-[#6B7280]">{feature.body}</p>
          </article>
        ))}
      </section>
      <footer className="border-t border-[#E5E7EB] bg-white p-6 text-center text-sm text-[#6B7280]">
        <span className="font-display text-xl text-[#0D7A5F]">SynaptiVerse</span> · Clinics in Akwa Ibom and Lagos
      </footer>
    </main>
  );
}
