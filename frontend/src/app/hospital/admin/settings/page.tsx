'use client';

import { useState } from 'react';
import { MessageSquare, PauseCircle, Shield, Smartphone, ToggleLeft, ToggleRight, Users } from 'lucide-react';
import { HospitalShell } from '@/components/HospitalShell';
import { cn } from '@/lib/utils';

const staffRows = [
  ['Dr. Udo Okon', 'DOCTOR', 'Assigned patient queue'],
  ['Nurse Iniobong Akpan', 'NURSE', 'Live triage lanes'],
  ['Admin Chiamaka Okafor', 'ADMIN', 'Tenant configuration'],
];

export default function HospitalSettingsPage() {
  const [paused, setPaused] = useState(false);
  const [smsRoute, setSmsRoute] = useState<'Africa’s Talking' | 'Twilio'>('Africa’s Talking');
  const [whatsappEnabled, setWhatsappEnabled] = useState(true);

  return (
    <HospitalShell>
      <main className="mx-auto grid max-w-7xl gap-5 p-4 md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Hospital Settings</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">Uyo Family Clinic account controls</h1>
        </div>
        <section className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <PauseCircle className="h-6 w-6 text-[#DC2626]" />
              <div>
                <h2 className="text-sm font-bold text-[#111827]">Global intake pause</h2>
                <p className="text-sm text-[#6B7280]">Stops patient triage intake for this hospital tenant.</p>
              </div>
            </div>
            <button onClick={() => setPaused((current) => !current)} className={cn('front-desk-target inline-flex items-center gap-2', paused ? 'bg-[#DC2626] text-white' : 'bg-[#2563EB] text-white')}>
              {paused ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
              {paused ? 'Paused' : 'Active'}
            </button>
          </div>
        </section>
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-[#2563EB]" />
              <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">SMS Route</p>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(['Africa’s Talking', 'Twilio'] as const).map((route) => (
                <button
                  key={route}
                  onClick={() => setSmsRoute(route)}
                  className={cn('front-desk-target border', smsRoute === route ? 'border-[#2563EB] bg-[#e0f2fe] text-[#2563EB]' : 'border-[#E5E7EB] bg-white text-[#6B7280]')}
                >
                  {route}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-[#2563EB]" />
                <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">WhatsApp Intake</p>
              </div>
              <button onClick={() => setWhatsappEnabled((current) => !current)} className="rounded-lg p-3 text-[#2563EB] hover:bg-[#e0f2fe]" aria-label="Toggle WhatsApp channel">
                {whatsappEnabled ? <ToggleRight className="h-6 w-6" /> : <ToggleLeft className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </section>
        <section className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-[#2563EB]" />
            <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Hospital Staff</p>
          </div>
          <div className="mt-4 overflow-hidden rounded-card border border-[#E5E7EB]">
            {staffRows.map(([name, role, scope]) => (
              <div key={name} className="data-row grid gap-2 border-b border-[#E5E7EB] last:border-b-0 sm:grid-cols-3">
                <span className="font-medium text-[#111827]">{name}</span>
                <span className="inline-flex items-center gap-2 text-[#6B7280]">
                  <Shield className="h-4 w-4" />
                  {role}
                </span>
                <span className="text-[#6B7280]">{scope}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </HospitalShell>
  );
}
