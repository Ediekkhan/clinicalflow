'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { TriageChat } from '@/components/patient/TriageChat';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientChatPage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <header className="mb-8"><p className="sv-kicker">AI symptom assessment</p><h1 className="mt-3 font-display text-4xl leading-tight text-[#10231e] sm:text-5xl">Tell us what you’re feeling.</h1><p className="mt-3 max-w-2xl leading-7 text-[#60706a]">Describe symptoms naturally. You’ll see urgency, the likely care specialty, a nearby facility, and the next available appointment.</p><div className="mt-6 grid gap-2 sm:grid-cols-3">{['1 · Describe symptoms','2 · Review urgency','3 · Continue to care'].map((step,index)=><div key={step} className={`rounded-full px-4 py-3 text-center text-xs font-black ${index===0?'bg-[#073d33] text-white':'border border-[#dbe2dc] bg-white text-[#60706a]'}`}>{step}</div>)}</div></header>
      <TriageChat />
    </DashboardShell>
  );
}
