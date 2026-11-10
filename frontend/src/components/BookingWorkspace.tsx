'use client';

import { CalendarDays, CheckCircle2, Loader2, Send } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { bookAppointment, createTicket, listOpenSlots } from '@/lib/api';
import type { Appointment, ProviderSlot } from '@/lib/types';
import { cn } from '@/lib/utils';

export function BookingWorkspace() {
  const [slots, setSlots] = useState<ProviderSlot[]>([]);
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [phone, setPhone] = useState('+234');
  const [complaint, setComplaint] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'done'>('idle');
  const [confirmation, setConfirmation] = useState<Appointment | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadSlots() {
      try {
        const data = await listOpenSlots();
        if (cancelled) return;
        const available = data.filter((slot) => !slot.is_locked && !slot.is_booked);
        setSlots(available);
        setSelectedSlotId(available[0]?.id ?? null);
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
    setError('');
    try {
      const ticket = await createTicket({
        customer_phone: phone,
        raw_intake_text: complaint,
      });
      if (!selectedSlotId) throw new Error('Choose an appointment slot');
      const appointment = await bookAppointment(ticket.id, selectedSlotId, phone);
      setConfirmation(appointment);
      setStatus('done');
    } catch (error) {
      console.error(error);
      setError(error instanceof Error ? error.message : 'Unable to complete this booking.');
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
                onClick={() => setSelectedSlotId(slot.id)}
                className={cn(
                  'front-desk-target border text-left',
                  selectedSlotId === slot.id
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
        disabled={!selectedSlotId || status === 'saving'}
        className="front-desk-target inline-flex items-center justify-center gap-2 bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-300"
      >
        {status === 'saving' ? <Loader2 className="h-5 w-5 animate-spin" /> : status === 'done' ? <CheckCircle2 className="h-5 w-5" /> : <Send className="h-5 w-5" />}
        {status === 'done' ? 'Booking sent' : 'Submit clinic ticket'}
      </button>
      {error ? <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p> : null}
      {confirmation ? (
        <section role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-950">
          <p className="flex items-center gap-2 font-bold"><CheckCircle2 className="h-5 w-5" /> Appointment confirmed</p>
          <p className="mt-2 text-sm">{confirmation.provider_name} · {confirmation.specialty}</p>
          <p className="text-sm">{new Intl.DateTimeFormat(undefined, { dateStyle: 'full', timeStyle: 'short' }).format(new Date(confirmation.starts_at))} · {confirmation.room_label}</p>
          <p className="mt-2 font-mono text-xs">Confirmation {confirmation.id}</p>
        </section>
      ) : null}
    </form>
  );
}
