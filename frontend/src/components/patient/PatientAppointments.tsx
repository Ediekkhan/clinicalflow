'use client';

import { useEffect, useState } from 'react';
import { CalendarCheck, Clock, FileText, MapPin } from 'lucide-react';
import { EmptyState } from '@/components/shared/EmptyState';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/lib/auth';

type AppointmentStatus = 'BOOKED' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW' | string;

type Appointment = {
  id: string;
  specialist_name?: string;
  provider_name?: string;
  specialty?: string;
  facility_name?: string;
  location?: string;
  scheduled_at?: string;
  starts_at?: string;
  status: AppointmentStatus;
  consultation_notes?: string | null;
};

type AppointmentEvent = {
  type?: string;
  appointment_id?: string;
  notes?: string;
  payload?: Appointment;
};

function formatDateTime(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function StatusBadge({ status }: { status: AppointmentStatus }) {
  switch (status) {
    case 'BOOKED':
      return <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs text-sky-600">Confirmed</span>;
    case 'CONFIRMED':
      return <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs text-emerald-600">Confirmed</span>;
    case 'COMPLETED':
      return <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs text-slate-500">✓ Done</span>;
    case 'CANCELLED':
      return <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs text-rose-600">Cancelled</span>;
    case 'NO_SHOW':
      return <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-600">Missed</span>;
    default:
      return <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600">{status}</span>;
  }
}

export function PatientAppointments() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [summaryId, setSummaryId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function cancelAppointment(id: string) {
    setBusyId(id);
    try {
      const updated = await api.patch(`/api/v1/appointments/${id}/cancel`, {});
      setAppointments((current) => current.map((appointment) => appointment.id === id ? { ...appointment, ...(updated as Appointment) } : appointment));
    } finally {
      setBusyId(null);
    }
  }

  useWebSocket<AppointmentEvent>('/api/v1/ws/triage', (event) => {
    if (event.type === 'appointment.updated' && event.payload?.id) {
      setAppointments((current) => {
        const remaining = current.filter((appointment) => appointment.id !== event.payload?.id);
        return [event.payload as Appointment, ...remaining];
      });
      return;
    }
    if (event.type !== 'APPOINTMENT_COMPLETED' || !event.appointment_id) return;
    setAppointments((current) =>
      current.map((appointment) =>
        appointment.id === event.appointment_id
          ? { ...appointment, status: 'COMPLETED', consultation_notes: event.notes ?? appointment.consultation_notes }
          : appointment,
      ),
    );
  });

  useEffect(() => {
    let cancelled = false;
    async function loadAppointments() {
      try {
        const data = await api.get('/api/v1/patient/appointments');
        if (!cancelled) setAppointments(Array.isArray(data) ? (data as Appointment[]) : []);
      } catch (error) {
        console.error(error);
        if (!cancelled) setAppointments([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadAppointments();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return (
      <section className="grid gap-4">
        {[1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-2xl bg-slate-100" />)}
      </section>
    );
  }

  if (appointments.length === 0) {
    return <EmptyState icon={CalendarCheck} title="No appointments scheduled" body="Your scheduled visits will appear here." />;
  }

  return (
    <section className="grid gap-4">
      {appointments.map((appointment) => {
        const completed = appointment.status === 'COMPLETED';
        const summaryOpen = summaryId === appointment.id;
        return (
          <article key={appointment.id} className={`rounded-2xl border border-slate-100 p-5 shadow-sm ${completed ? 'bg-slate-50 text-slate-600' : 'bg-white'}`}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex gap-4">
                <div className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-[#0b5d4b]">
                  <CalendarCheck className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">{appointment.specialist_name ?? appointment.provider_name ?? ''}</h3>
                  {appointment.specialty ? <p className="text-sm text-slate-500">{appointment.specialty}</p> : null}
                  {[appointment.facility_name, appointment.location].filter(Boolean).length ? (
                    <p className="mt-2 flex items-center gap-2 text-sm text-slate-500">
                      <MapPin className="h-4 w-4" />
                      {[appointment.facility_name, appointment.location].filter(Boolean).join(' · ')}
                    </p>
                  ) : null}
                </div>
              </div>
              <div className="text-right">
                <StatusBadge status={appointment.status} />
                <p className="mt-2 flex items-center justify-end gap-2 text-sm font-semibold text-slate-700">
                  <Clock className="h-4 w-4" />
                  {formatDateTime(appointment.scheduled_at ?? appointment.starts_at)}
                </p>
              </div>
            </div>
            {completed ? (
              <div className="mt-4 border-t border-slate-200 pt-4">
                <button type="button" onClick={() => setSummaryId(summaryOpen ? null : appointment.id)} className="inline-flex items-center gap-2 text-sm font-semibold text-[#0b5d4b]">
                  <FileText className="h-4 w-4" />
                  View Summary →
                </button>
                {summaryOpen ? <p className="mt-3 rounded-xl bg-white p-4 text-sm text-slate-600">{appointment.consultation_notes || 'No notes recorded'}</p> : null}
              </div>
            ) : appointment.status === 'BOOKED' ? (
              <div className="mt-4 border-t border-slate-100 pt-4 text-right">
                <button type="button" disabled={busyId === appointment.id} onClick={() => void cancelAppointment(appointment.id)} className="rounded-lg bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-100 disabled:opacity-50">
                  {busyId === appointment.id ? 'Cancelling…' : 'Cancel appointment'}
                </button>
              </div>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
