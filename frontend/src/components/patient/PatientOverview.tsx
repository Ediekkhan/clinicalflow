'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Activity, Calendar, CreditCard, Lightbulb, Ticket } from 'lucide-react';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { Badge } from '@/components/shared/Badge';
import { StatCard } from '@/components/shared/StatCard';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export function PatientOverview() {
  const [mood, setMood] = useState('Good');

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] p-6 text-white shadow-sm">
          <h2 className="font-display text-3xl">Good morning, Adaeze</h2>
          <p className="mt-1 text-blue-50">How are you feeling today?</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {['Good', 'Okay', 'Not well'].map((item) => (
              <button key={item} onClick={() => setMood(item)} className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${mood === item ? 'bg-white text-[#2563EB]' : 'bg-white/10 text-white hover:bg-white/20'}`}>
                {item === 'Good' ? 'Good' : item === 'Okay' ? 'Okay' : 'Not well'}
              </button>
            ))}
          </div>
          {mood === 'Not well' ? (
            <Link href="/dashboard/chat" className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-[#2563EB]">
              Start a symptom check
              <Activity className="h-4 w-4" />
            </Link>
          ) : null}
        </section>
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Link href="/dashboard/queue"><StatCard title="Active Tickets" value="1" sub="URGENT - Cardiologist" tone="amber" icon={Ticket} /></Link>
          <StatCard title="Next Appointment" value="Today 3:00 PM" sub="Dr. Okon - Cardiology" tone="sky" icon={Calendar} />
          <Link href="/dashboard/queue"><StatCard title="Queue Position" value="#3" sub="Live queue position" tone="sky" icon={Activity} /></Link>
          <Link href="/dashboard/card"><StatCard title="Health Card" value="SV-AKS" sub="Digital card ready" tone="slate" icon={CreditCard} /></Link>
        </section>
        <section className="grid gap-5 xl:grid-cols-[1fr_0.45fr]">
          <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-slate-900">Recent Activity</h3>
            <div className="mt-4 space-y-3">
              {entity.activity.map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-xl border border-slate-100 p-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-[#2563EB]" />
                  <div>
                    <p className="text-sm text-slate-700">{item}</p>
                    <p className="text-xs text-slate-400">2h ago</p>
                  </div>
                </div>
              ))}
            </div>
          </article>
          <article className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-[#2563EB]" />
              <h3 className="font-semibold text-slate-900">Today&apos;s Health Tip</h3>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Staying hydrated helps prevent kidney stones, which are common in hot climates like Akwa Ibom. Keep water nearby during long clinic waits.
            </p>
            <Badge tone="success">Cached daily</Badge>
          </article>
        </section>
      </div>
    </DashboardShell>
  );
}

