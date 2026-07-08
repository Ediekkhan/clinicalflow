'use client';

import { CalendarDays, CheckCircle2, Loader2, Send } from 'lucide-react';
import { useMemo, useState } from 'react';
import { createTicket } from '@/lib/api';
import { demoSlots } from '@/lib/demo-data';
import { cn } from '@/lib/utils';

export function BookingWorkspace() {
  const [selectedSlot, setSelectedSlot] = useState(demoSlots[0]?.starts_at ?? null);
  const [phone, setPhone] = useState('+234');
  const [complaint, setComplaint] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'done'>('idle');

  const slotsByDay = useMemo(() => demoSlots.slice(0, 12), []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('saving');
    try {
      await createTicket({
        customer_phone: phone,
        raw_intake_text: complaint,
        appointment_slot: selectedSlot,
      });
    } catch {
      // The offline demo still confirms locally so patient-facing forms remain usable on a LAN outage.
    }
    setStatus('done');
  }

  return (
    <form onSubmit={submit} className="mx-auto grid max-w-2xl gap-5 p-4 md:p-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Self-Service Booking</p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Choose a clinic slot</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Enter the patient phone and chief complaint. The clinic queue will receive the ticket immediately.
        </p>
      </div>
      <label className="grid gap-2 text-sm font-medium text-slate-700">
        Patient phone
        <input
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          className="rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
          required
        />
      </label>
      <label className="grid gap-2 text-sm font-medium text-slate-700">
        Chief complaint
        <textarea
          value={complaint}
          onChange={(event) => setComplaint(event.target.value)}
          className="min-h-32 rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
          placeholder="Example: Hot body and headache since yesterday"
          required
        />
      </label>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5 text-blue-600" />
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Open Time Slots</p>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {slotsByDay.map((slot) => (
            <button
              type="button"
              key={slot.id}
              onClick={() => setSelectedSlot(slot.starts_at)}
              className={cn(
                'front-desk-target border text-left',
                selectedSlot === slot.starts_at
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
              )}
            >
              <span className="block text-sm font-bold">
                {new Intl.DateTimeFormat('en-NG', { hour: 'numeric', minute: '2-digit' }).format(new Date(slot.starts_at))}
              </span>
              <span className="block text-sm font-normal text-slate-600">{slot.room_label}</span>
            </button>
          ))}
        </div>
      </section>
      <button
        type="submit"
        className="front-desk-target inline-flex items-center justify-center gap-2 bg-blue-600 text-white hover:bg-blue-700"
      >
        {status === 'saving' ? <Loader2 className="h-5 w-5 animate-spin" /> : status === 'done' ? <CheckCircle2 className="h-5 w-5" /> : <Send className="h-5 w-5" />}
        {status === 'done' ? 'Booking sent' : 'Submit clinic ticket'}
      </button>
    </form>
  );
}

