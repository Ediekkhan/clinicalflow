'use client';

import { CalendarDays, CheckCircle2, Loader2, Send } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { createTicket, listOpenSlots } from '@/lib/api';
import type { ProviderSlot } from '@/lib/types';
import { cn } from '@/lib/utils';

export function BookingWorkspace() {
  const [slots, setSlots] = useState<ProviderSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [phone, setPhone] = useState('+234');
  const [complaint, setComplaint] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'done'>('idle');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadSlots() {
      try {
        const data = await listOpenSlots();
        if (cancelled) return;
        setSlots(data);
        setSelectedSlot(data[0]?.starts_at ?? null);
      } catch (error) {
        console.error(error);
        if (!cancelled) setSlots([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadSlots();
    return () => {
      cancelled = true;
    };
  }, []);

  const slotsByDay = useMemo(() => slots.slice(0, 12), [slots]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('saving');
    try {
      await createTicket({
        customer_phone: phone,
        raw_intake_text: complaint,
        appointment_slot: selectedSlot,
      });
      setStatus('done');
    } catch (error) {
      console.error(error);
      setStatus('idle');
    }
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
          placeholder="Describe the main concern"
          required
        />
      </label>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5 text-blue-600" />
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Open Time Slots</p>
        </div>
        {isLoading ? (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse rounded-lg bg-slate-100" />)}</div>
        ) : slotsByDay.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-slate-200 p-5 text-center text-sm text-slate-500">No open slots available</p>
        ) : (
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
                  {new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(slot.starts_at))}
                </span>
                <span className="block text-sm font-normal text-slate-600">{slot.room_label}</span>
              </button>
            ))}
          </div>
        )}
      </section>
      <button
        type="submit"
        disabled={!selectedSlot || status === 'saving'}
        className="front-desk-target inline-flex items-center justify-center gap-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-300"
      >
        {status === 'saving' ? <Loader2 className="h-5 w-5 animate-spin" /> : status === 'done' ? <CheckCircle2 className="h-5 w-5" /> : <Send className="h-5 w-5" />}
        {status === 'done' ? 'Booking sent' : 'Submit clinic ticket'}
      </button>
    </form>
  );
}
