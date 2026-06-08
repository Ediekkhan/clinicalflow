'use client';

import { useState } from 'react';
import { ChevronRight, UsersRound } from 'lucide-react';
import { demoTickets } from '@/lib/demo-data';
import { cn } from '@/lib/utils';

export default function MyVisitPage() {
  const [active, setActive] = useState(demoTickets[0]);
  const sharedPhoneTickets = demoTickets.slice(0, 3);

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto grid max-w-4xl gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Digital Ticket</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Live queue position</h1>
        </div>
        <section className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-6 text-center shadow-sm">
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">[PROJECT_NAME] Visit Pass</p>
          <p className="mt-4 break-words font-mono text-3xl font-bold tracking-tight text-slate-900 sm:text-5xl">{active.ticket_number}</p>
          <p className="mt-4 text-2xl font-bold tracking-tight text-emerald-700">You are #3 in line for Room 2</p>
          <p className="mt-2 text-sm text-slate-600">{active.assigned_specialty} · {active.urgency_level}</p>
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2">
            <UsersRound className="h-5 w-5 text-emerald-600" />
            <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Shared Phone Group</p>
          </div>
          <div className="mt-4 grid gap-2">
            {sharedPhoneTickets.map((ticket) => (
              <button
                key={ticket.id}
                onClick={() => setActive(ticket)}
                className={cn(
                  'data-row flex items-center justify-between rounded-lg border text-left',
                  active.id === ticket.id
                    ? 'border-emerald-600 bg-emerald-50 text-emerald-700'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                )}
              >
                <span>
                  <span className="block font-mono font-bold">{ticket.ticket_number}</span>
                  <span className="block text-sm">{ticket.assigned_specialty}</span>
                </span>
                <ChevronRight className="h-4 w-4" />
              </button>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
