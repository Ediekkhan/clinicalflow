'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Calendar, MapPin } from 'lucide-react';
import { Badge } from '@/components/shared/Badge';
import { api } from '@/lib/auth';

type TriageResponse = {
  messages?: string[];
  condition_name?: string;
  urgency?: 'CRITICAL' | 'URGENT' | 'ROUTINE';
  severity_message?: string;
  nearest_clinic?: { clinic_name?: string; address?: string; distance_km?: number; specialist_name?: string };
  appointment_slot?: { slot_start?: string; specialist_name?: string; specialty?: string; room_label?: string };
  ticket?: { id?: string; ticket_number?: string };
};

function formatSlot(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function TriageChat() {
  const router = useRouter();
  const [text, setText] = useState('');
  const [userMessage, setUserMessage] = useState('');
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const responseComplete = Boolean(result && !isLoading);

  async function submitSymptoms() {
    const symptomText = text.trim();
    if (!symptomText) return;
    setUserMessage(symptomText);
    setText('');
    setResult(null);
    setError(null);
    setIsLoading(true);

    try {
      const data = (await api.post('/api/v1/patient/triage', { symptom_description: symptomText })) as TriageResponse;
      setResult(data);
    } catch (caught) {
      console.error(caught);
      setError(caught instanceof Error ? caught.message : 'Unable to complete triage right now.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="flex min-h-[calc(100vh-11rem)] flex-col overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-semibold text-slate-900">SynaptiVerse AI</h2>
          <p className="text-xs text-slate-400">Powered by Claude</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">
          <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
          Live
        </span>
      </header>
      <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-5">
        <div className="max-w-[82%] rounded-2xl rounded-bl-sm bg-white p-4 text-sm text-slate-700 shadow-sm">
          Tell me what you are experiencing. Use English, Pidgin, or whatever feels natural.
        </div>
        {userMessage ? <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-[#2563EB] p-4 text-sm text-white">{userMessage}</div> : null}
        {isLoading ? (
          <div className="max-w-[85%] rounded-2xl bg-white p-4 shadow-sm">
            <div className="h-4 w-48 animate-pulse rounded bg-slate-100" />
            <div className="mt-3 h-4 w-64 animate-pulse rounded bg-slate-100" />
          </div>
        ) : null}
        {error ? <div role="alert" className="max-w-[85%] rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
        {result ? (
          <>
            {(result.messages ?? []).map((message, index) => (
              <div key={`${message}-${index}`} className="max-w-[85%] rounded-2xl bg-white p-4 text-sm text-slate-700 shadow-sm">{message}</div>
            ))}
            {(result.urgency || result.condition_name || result.severity_message) ? (
              <div className="max-w-[85%] rounded-2xl bg-white p-4 shadow-sm">
                {result.urgency ? <Badge tone={result.urgency === 'CRITICAL' ? 'critical' : result.urgency === 'URGENT' ? 'urgent' : 'routine'}>{result.urgency}</Badge> : null}
                {result.condition_name ? <h3 className="mt-3 font-semibold text-slate-900">{result.condition_name}</h3> : null}
                {result.severity_message ? <p className="mt-2 text-sm text-slate-600">{result.severity_message}</p> : null}
              </div>
            ) : null}
            {result.nearest_clinic ? (
              <div className="max-w-[85%] rounded-2xl border border-blue-100 bg-white p-4 shadow-sm">
                <div className="flex gap-3">
                  <MapPin className="h-5 w-5 text-[#2563EB]" />
                  <div>
                    <p className="font-semibold text-slate-900">{result.nearest_clinic.clinic_name ?? ''}</p>
                    <p className="text-sm text-slate-500">{[result.nearest_clinic.address, result.nearest_clinic.specialist_name].filter(Boolean).join(' - ')}</p>
                  </div>
                </div>
              </div>
            ) : null}
            {result.appointment_slot ? (
              <div className="max-w-[85%] rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
                <div className="flex gap-3">
                  <Calendar className="h-5 w-5 text-[#2563EB]" />
                  <div className="w-full">
                    <p className="font-semibold text-slate-900">Suggested available appointment</p>
                    <p className="text-sm text-slate-500">{[formatSlot(result.appointment_slot.slot_start), result.appointment_slot.specialist_name, result.appointment_slot.specialty, result.appointment_slot.room_label].filter(Boolean).join(' - ')}</p>
                    {responseComplete ? (
                      <button
                        onClick={() => router.push('/dashboard/queue')}
                        className="mt-4 flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-[#0D7A5F] px-4 py-3 text-sm font-medium text-white transition-all duration-200 hover:bg-[#0a6550] active:scale-95"
                      >
                        🎫 View My Ticket →
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}
            {result.urgency === 'CRITICAL' ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
                <p className="font-bold">This may be a medical emergency. Please seek immediate care.</p>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
      <footer className="border-t border-slate-100 bg-white p-4">
        <div className="relative">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            minLength={2}
            maxLength={2000}
            placeholder="Describe how you feel..."
            className="min-h-24 w-full resize-none rounded-2xl border border-slate-200 p-4 pr-24 text-sm outline-none transition focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100"
          />
          <span className="absolute right-4 top-3 text-xs text-slate-400">{text.length}/2000</span>
        </div>
        <div className="mt-3 flex justify-end gap-2">
          <button
            type="button"
            disabled={!text.trim() || isLoading}
            onClick={() => void submitSymptoms()}
            className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Send
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </footer>
    </section>
  );
}
