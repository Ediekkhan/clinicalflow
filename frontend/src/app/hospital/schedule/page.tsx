'use client';

import { useState } from 'react';
import { Ban, CalendarPlus } from 'lucide-react';
import { HospitalShell } from '@/components/HospitalShell';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { patientTickets } from '@/lib/syn-data';
import { cn } from '@/lib/utils';

const hours = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'];

export default function HospitalSchedulePage() {
  const [blocked, setBlocked] = useState<string[]>(['12:00']);
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <HospitalShell>
      <main className="mx-auto grid max-w-7xl gap-5 p-4 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Doctor Schedule</p>
            <h1 className="font-display text-4xl text-[#111827] md:text-5xl">My hospital calendar</h1>
          </div>
          <button onClick={() => setBlocked((current) => [...current, '15:00'])} className="front-desk-target inline-flex items-center gap-2 bg-[#2563EB] text-white">
            <CalendarPlus className="h-5 w-5" />
            Block Time
          </button>
        </div>
        <section className="grid gap-3 md:grid-cols-4">
          {hours.map((hour, index) => {
            const ticket = patientTickets[index % patientTickets.length];
            const unavailable = blocked.includes(hour);
            return (
              <button
                key={hour}
                onClick={() => setSelected(hour)}
                className={cn('min-h-32 rounded-card border p-4 text-left shadow-sm', unavailable ? 'border-[#E5E7EB] bg-slate-100 text-[#6B7280]' : 'border-[#E5E7EB] bg-white hover:border-[#2563EB]')}
              >
                <p className="font-mono font-bold">{hour}</p>
                {unavailable ? (
                  <p className="mt-4 inline-flex items-center gap-2 text-sm font-bold">
                    <Ban className="h-4 w-4" />
                    Unavailable
                  </p>
                ) : (
                  <div className="mt-4 grid gap-2">
                    <p className="text-sm font-bold text-[#111827]">{ticket.patient_name}</p>
                    <UrgencyBadge level={ticket.urgency_level} />
                    <p className="text-xs text-[#6B7280]">{ticket.matched_condition_name}</p>
                  </div>
                )}
              </button>
            );
          })}
        </section>
        {selected ? (
          <aside className="rounded-card border border-[#E5E7EB] bg-white p-5 shadow-sm">
            <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Appointment Details</p>
            <h2 className="font-display text-3xl text-[#111827]">{selected} slot</h2>
            <p className="mt-2 text-sm text-[#6B7280]">
              Changes post through the hospital appointment APIs and notify patients by SMS/app notification.
            </p>
          </aside>
        ) : null}
      </main>
    </HospitalShell>
  );
}
