'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/components/shared/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';

type HistoryEvent = {
  id?: string;
  type?: string;
  title?: string;
  summary?: string;
  provider_name?: string;
  facility_name?: string;
  status?: string;
  created_at?: string;
  tone?: 'rose' | 'sky' | 'violet' | 'routine' | 'success';
};

function formatDate(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function PatientHistory() {
  const [events, setEvents] = useState<HistoryEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadHistory() {
      try {
        const data = await api.get('/api/v1/patient/history');
        if (!cancelled) setEvents(Array.isArray(data) ? (data as HistoryEvent[]) : []);
      } catch (error) {
        console.error(error);
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <div className="mb-5 flex flex-wrap gap-2">
        {['All', 'Triage Sessions', 'Appointments', 'Prescriptions'].map((filter, index) => (
          <button key={filter} className={`rounded-full px-4 py-2 text-sm font-semibold ${index === 0 ? 'bg-[#0b5d4b] text-white' : 'bg-slate-100 text-slate-600'}`}>{filter}</button>
        ))}
      </div>
      {isLoading ? (
        <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-slate-100" />)}</div>
      ) : events.length === 0 ? (
        <EmptyState title="No results available" body="Your health history will appear here after visits, prescriptions, or lab results are available." />
      ) : (
        <div className="relative space-y-5 border-l border-slate-200 pl-6">
          {events.map((event, index) => {
            const tone = event.tone ?? (event.status === 'CRITICAL' ? 'rose' : 'success');
            return (
              <article key={event.id ?? index} className="relative rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                <span className={`absolute -left-[31px] top-5 h-3 w-3 rounded-full ${tone === 'rose' ? 'bg-rose-500' : tone === 'sky' ? 'bg-blue-500' : tone === 'violet' ? 'bg-violet-500' : 'bg-blue-500'}`} />
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    {event.created_at ? <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{formatDate(event.created_at)}</p> : null}
                    <h3 className="mt-1 font-semibold text-slate-900">{event.title ?? event.summary ?? event.type}</h3>
                    {[event.provider_name, event.facility_name].filter(Boolean).length ? <p className="mt-1 text-sm text-slate-500">{[event.provider_name, event.facility_name].filter(Boolean).join(' · ')}</p> : null}
                  </div>
                  {event.status ? <Badge tone={tone === 'rose' ? 'rose' : tone === 'sky' ? 'success' : tone === 'violet' ? 'violet' : 'routine'}>{event.status}</Badge> : null}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
