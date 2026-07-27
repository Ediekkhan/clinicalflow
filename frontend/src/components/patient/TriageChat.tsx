'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Calendar, MapPin } from 'lucide-react';
import { Badge } from '@/components/shared/Badge';
import { useGeolocation } from '@/hooks/useGeolocation';
import { api } from '@/lib/auth';

type IllnessSeverity = 'MILD' | 'MODERATE' | 'SEVERE';

type TriageResponse = {
  messages?: string[];
  condition_name?: string;
  possible_illness?: string;
  diagnosis_disclaimer?: string;
  urgency?: 'CRITICAL' | 'URGENT' | 'ROUTINE';
  severity?: IllnessSeverity;
  severity_label?: string;
  severity_message?: string;
  nearest_clinic?: { clinic_name?: string; address?: string; distance_km?: number | null; specialist_name?: string | null; match_basis?: string };
  appointment_slot?: { slot_start?: string; specialist_name?: string; specialty?: string; room_label?: string };
  ticket?: { id?: string; ticket_number?: string };
};

function severityTone(severity?: IllnessSeverity) {
  if (severity === 'SEVERE') return 'critical';
  if (severity === 'MODERATE') return 'urgent';
  return 'routine';
}

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
  const { coords, error: locationError, isLoading: isLocationLoading, requestLocation } = useGeolocation();
  const responseComplete = Boolean(result && !isLoading);

  async function submitSymptoms() {
    const symptomText = text.trim();
    if (!symptomText) return;
    if (!coords) {
      setError('Add your current location before analysis so we can route this ticket to the nearest registered hospital.');
      return;
    }
    setUserMessage(symptomText);
    setText('');
    setResult(null);
    setError(null);
    setIsLoading(true);

    const payload = { symptom_description: symptomText, latitude: coords.latitude, longitude: coords.longitude };
    try {
      const data = (await api.post('/api/v1/patient/triage', payload)) as TriageResponse;
      setResult(data);
    } catch (caught) {
      console.error(caught);
      try {
        const preview = (await api.post('/api/v1/public/triage-preview', payload)) as TriageResponse;
        setResult({
          ...preview,
          messages: ['I analyzed your symptoms using the public triage service.', ...(preview.messages ?? [])],
        });
      } catch (fallbackError) {
        console.error(fallbackError);
        setError(fallbackError instanceof Error ? fallbackError.message : 'Unable to complete triage right now.');
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="flex min-h-[640px] flex-col overflow-hidden rounded-[2rem] border border-[#dbe2dc] bg-white shadow-[0_24px_70px_rgba(7,61,51,.08)]">
      <header className="flex items-center justify-between border-b border-[#dbe2dc] px-5 py-4 sm:px-7">
        <div>
          <h2 className="font-black text-[#10231e]">Clinical routing assistant</h2>
          <p className="text-xs text-[#60706a]">Private, guided symptom intake</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-[#e9f6f1] px-3 py-1.5 text-xs font-black text-[#0b5d4b]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[#0b5d4b]" />
          Ready
        </span>
      </header>
      <div className="flex-1 space-y-4 overflow-y-auto bg-[#f7f8f3] p-5 sm:p-7">
        <div className="max-w-[88%] rounded-2xl rounded-bl-sm border border-[#dbe2dc] bg-white p-4 text-sm leading-6 text-[#50615b] shadow-sm sm:max-w-[70%]">
          Start anywhere: tell me what hurts, when it started, and anything that makes it better or worse. English and Pidgin are both welcome.
        </div>
        <div className="max-w-[92%] rounded-2xl border border-[#dbe2dc] bg-white p-4 text-sm text-[#50615b] shadow-sm sm:max-w-[78%]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-[#0b5d4b]" />
              <span className="font-semibold text-[#10231e]">{coords ? 'Location added' : 'Add your location'}</span>
            </div>
            <button type="button" onClick={requestLocation} disabled={isLocationLoading} className="min-h-10 rounded-full bg-[#e9f6f1] px-4 text-xs font-black text-[#0b5d4b] disabled:opacity-60">
              {isLocationLoading ? 'Requesting...' : coords ? 'Refresh location' : 'Use my location'}
            </button>
          </div>
          <p className="mt-2 text-xs leading-5 text-[#60706a]">
            {coords ? 'Your coordinates will be used only to select the nearest eligible registered hospital for this ticket.' : 'We need browser location permission before creating a ticket, so we do not guess the nearest hospital.'}
          </p>
          {locationError ? <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">{locationError}</p> : null}
        </div>
        {userMessage ? <div className="ml-auto max-w-[88%] rounded-2xl rounded-br-sm bg-[#073d33] p-4 text-sm leading-6 text-white sm:max-w-[70%]">{userMessage}</div> : null}
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
              <div className="max-w-[92%] rounded-2xl border border-[#dbe2dc] bg-white p-5 shadow-sm sm:max-w-[78%]">
                <div className="flex flex-wrap gap-2">
                  {result.urgency ? <Badge tone={result.urgency === 'CRITICAL' ? 'critical' : result.urgency === 'URGENT' ? 'urgent' : 'routine'}>{result.urgency}</Badge> : null}
                  {result.severity ? <Badge tone={severityTone(result.severity)}>Severity: {result.severity_label ?? result.severity}</Badge> : null}
                </div>
                {result.possible_illness ? (
                  <div className="mt-4 rounded-xl bg-[#f7f8f3] p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-[#60706a]">Possible illness</p>
                    <p className="mt-1 font-semibold text-slate-900">{result.possible_illness}</p>
                    {result.diagnosis_disclaimer ? <p className="mt-2 text-xs leading-5 text-slate-500">{result.diagnosis_disclaimer}</p> : null}
                  </div>
                ) : null}
                {result.condition_name ? <p className="mt-3 text-sm text-slate-500">Clinical pattern: <span className="font-semibold text-slate-700">{result.condition_name}</span></p> : null}
                {result.severity_message ? <p className="mt-2 text-sm text-slate-600">{result.severity_message}</p> : null}
              </div>
            ) : null}
            {result.nearest_clinic ? (
              <div className="max-w-[85%] rounded-2xl border border-blue-100 bg-white p-4 shadow-sm">
                <div className="flex gap-3">
                  <MapPin className="h-5 w-5 text-[#0b5d4b]" />
                  <div>
                    <p className="font-semibold text-slate-900">{result.nearest_clinic.clinic_name ?? ''}</p>
                    <p className="text-sm text-slate-500">{[result.nearest_clinic.address, result.nearest_clinic.specialist_name].filter(Boolean).join(' - ')}</p>
                    {typeof result.nearest_clinic.distance_km === 'number' ? <p className="mt-1 text-xs font-semibold text-[#60706a]">Approx. {result.nearest_clinic.distance_km} km away</p> : null}
                    {result.nearest_clinic.match_basis ? <p className="mt-1 text-xs text-slate-400">{result.nearest_clinic.match_basis}</p> : null}
                  </div>
                </div>
              </div>
            ) : null}
            {result.appointment_slot ? (
              <div className="max-w-[85%] rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
                <div className="flex gap-3">
                  <Calendar className="h-5 w-5 text-[#0b5d4b]" />
                  <div className="w-full">
                    <p className="font-semibold text-slate-900">Suggested available appointment</p>
                    <p className="text-sm text-slate-500">{[formatSlot(result.appointment_slot.slot_start), result.appointment_slot.specialist_name, result.appointment_slot.specialty, result.appointment_slot.room_label].filter(Boolean).join(' - ')}</p>
                    {responseComplete ? (
                      <button
                        onClick={() => router.push('/dashboard/queue')}
                        className="mt-4 flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-[#0D7A5F] px-4 py-3 text-sm font-medium text-white transition-all duration-200 hover:bg-[#0a6550] active:scale-95"
                      >
                        View My Ticket {"->"}
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
      <footer className="border-t border-[#dbe2dc] bg-white p-4 sm:p-6">
        <div className="relative">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            minLength={2}
            maxLength={2000}
            placeholder="Example: I have had a high fever and feel weak for two days..."
            aria-label="Describe your symptoms"
            className="min-h-28 w-full resize-none rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] p-4 pr-24 text-sm leading-6 outline-none transition focus:border-[#0b5d4b]"
          />
          <span className="absolute right-4 top-3 text-xs text-slate-400">{text.length}/2000</span>
        </div>
        <div className="mt-3 flex justify-end gap-2">
          <button
            type="button"
            disabled={!text.trim() || !coords || isLoading}
            onClick={() => void submitSymptoms()}
            className="sv-button-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            Analyze symptoms
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </footer>
    </section>
  );
}
