'use client';

import { CheckCircle2, Clock, Stethoscope, X } from 'lucide-react';
import { type Ticket } from '@/lib/types';
import { cn } from '@/lib/utils';

export function PatientContextDrawer({
  ticket,
  open,
  onClose,
  onSetBeingSeen,
  onResolve,
}: {
  ticket: Ticket | null;
  open: boolean;
  onClose: () => void;
  onSetBeingSeen: (ticketId: string) => void;
  onResolve: (ticketId: string) => void;
}) {
  return (
    <div
      aria-hidden={!open}
      className={cn(
        'fixed inset-0 z-40 transition',
        open ? 'pointer-events-auto bg-slate-950/25' : 'pointer-events-none bg-transparent',
      )}
    >
      <aside
        className={cn(
          'absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-200 p-4 md:p-6">
          <div>
            <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Patient Context</p>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              {ticket?.ticket_number ?? 'No ticket selected'}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-3 text-slate-600 hover:bg-slate-100"
            aria-label="Close patient context"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {ticket ? (
          <div className="grid flex-1 gap-4 overflow-y-auto p-4 md:p-6">
            <section className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Raw Intake Message</p>
              <p className="mt-3 text-sm leading-6 text-slate-900">
                {ticket.raw_intake_text || 'No free-text intake captured.'}
              </p>
            </section>

            <section className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Extracted Symptoms</p>
                <p className="mt-3 text-sm text-slate-900">{ticket.extracted_symptoms || 'unclassified'}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Graph Route</p>
                <p className="mt-3 text-sm text-slate-900">{ticket.assigned_specialty || 'Front Desk Review'}</p>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Clinical Actions</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => onSetBeingSeen(ticket.id)}
                  className="front-desk-target inline-flex items-center justify-center gap-2 bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Stethoscope className="h-5 w-5" />
                  Start review
                </button>
                <button
                  type="button"
                  onClick={() => onResolve(ticket.id)}
                  className="front-desk-target inline-flex items-center justify-center gap-2 bg-slate-900 text-white hover:bg-slate-800"
                >
                  <CheckCircle2 className="h-5 w-5" />
                  Complete
                </button>
              </div>
            </section>

            {ticket.pendingSync ? (
              <div className="inline-flex items-center gap-2 rounded-lg bg-amber-50 px-4 py-3.5 text-sm font-medium text-amber-700">
                <Clock className="h-4 w-4" />
                ⏱️ Pending Sync
              </div>
            ) : null}
          </div>
        ) : null}
      </aside>
    </div>
  );
}

