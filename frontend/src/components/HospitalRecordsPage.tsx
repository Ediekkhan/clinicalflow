'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CalendarDays, RefreshCcw, Search, Stethoscope, Users } from 'lucide-react';
import { listHospitalDepartments, listHospitalPatients, listHospitalSpecialists } from '@/lib/api';
import type { HospitalDepartment, HospitalPatient, HospitalSpecialist } from '@/lib/types';
import { cn } from '@/lib/utils';

type Mode = 'queue' | 'specialists' | 'departments';
type Row = HospitalPatient | HospitalSpecialist | HospitalDepartment;

const filterOptions: Record<Mode, string[]> = {
  queue: ['All patients', 'Critical', 'Urgent', 'Routine', 'Awaiting doctor', 'Appointment confirmed', 'Checked in', 'Being seen', 'Completed'],
  specialists: ['All specialists', 'Available', 'On duty', 'Off duty', 'Verified'],
  departments: ['All departments', 'Available', 'Limited'],
};

const emptyCopy: Record<Mode, { title: string; body: string }> = {
  queue: { title: 'No patients routed here yet', body: 'Patients routed or appointed to this hospital will appear here.' },
  specialists: { title: 'No verified specialists yet', body: 'Doctors and specialists verified for this hospital will appear here.' },
  departments: { title: 'No departments configured yet', body: 'Departments added by the hospital administrator will appear here.' },
};

function statusTone(value?: string | null) {
  const normalized = String(value ?? '').toUpperCase();
  if (normalized.includes('CRITICAL') || normalized.includes('CANCELLED') || normalized.includes('INACTIVE')) return 'bg-rose-50 text-rose-700 ring-rose-200';
  if (normalized.includes('URGENT') || normalized.includes('AWAITING') || normalized.includes('LIMITED')) return 'bg-amber-50 text-amber-700 ring-amber-200';
  if (normalized.includes('AVAILABLE') || normalized.includes('BOOKED') || normalized.includes('VERIFIED')) return 'bg-emerald-50 text-emerald-700 ring-emerald-200';
  return 'bg-slate-100 text-slate-600 ring-slate-200';
}

function Badge({ value }: { value?: string | null }) {
  if (!value) return null;
  return <span className={cn('inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1', statusTone(value))}>{value.replaceAll('_', ' ')}</span>;
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function normalizeDepartment(value: unknown): HospitalDepartment {
  const department = (value ?? {}) as Partial<HospitalDepartment>;
  return {
    id: department.id ?? '',
    name: department.name ?? 'Unnamed department',
    code: department.code ?? '',
    description: department.description ?? null,
    status: department.status ?? 'UNKNOWN',
    coordinator: department.coordinator ?? null,
    total_doctors: Number(department.total_doctors ?? 0),
    available_doctors: Number(department.available_doctors ?? 0),
    specialists_on_duty: Number(department.specialists_on_duty ?? 0),
    nurses_on_duty: Number(department.nurses_on_duty ?? 0),
    patients_waiting: Number(department.patients_waiting ?? 0),
    appointments_today: Number(department.appointments_today ?? 0),
    average_wait_time_minutes: department.average_wait_time_minutes ?? null,
    capacity_status: department.capacity_status ?? 'UNKNOWN',
    available_doctors_list: Array.isArray(department.available_doctors_list) ? department.available_doctors_list : [],
  };
}

function listItems<T>(response: { items?: T[] } | T[] | null | undefined): T[] {
  if (Array.isArray(response)) return response;
  if (response && Array.isArray(response.items)) return response.items;
  return [];
}
function rowText(row: Row) {
  return JSON.stringify(row).toLowerCase();
}

function matchesFilter(mode: Mode, row: Row, filter: string) {
  if (filter.startsWith('All')) return true;
  if (mode === 'queue') {
    const item = row as HospitalPatient;
    if (filter === 'Critical') return item.urgency === 'CRITICAL';
    if (filter === 'Urgent') return item.urgency === 'URGENT';
    if (filter === 'Routine') return item.urgency === 'ROUTINE';
    if (filter === 'Awaiting doctor') return item.assignment_status === 'AWAITING_ASSIGNMENT';
    if (filter === 'Appointment confirmed') return item.assignment_status === 'APPOINTMENT_CONFIRMED';
    if (filter === 'Being seen') return item.queue_status === 'BEING_SEEN';
    if (filter === 'Completed') return item.queue_status === 'RESOLVED' || item.status === 'COMPLETED';
    if (filter === 'Checked in') return item.status === 'CHECKED_IN';
  }
  if (mode === 'specialists') {
    const item = row as HospitalSpecialist;
    if (filter === 'Available') return item.availability === 'AVAILABLE';
    if (filter === 'On duty') return item.is_on_duty;
    if (filter === 'Off duty') return !item.is_on_duty;
    if (filter === 'Verified') return item.license_status === 'VERIFIED';
  }
  if (mode === 'departments') {
    const item = row as HospitalDepartment;
    if (filter === 'Available') return item.capacity_status === 'AVAILABLE';
    if (filter === 'Limited') return item.capacity_status !== 'AVAILABLE';
  }
  return true;
}

function iconForMode(mode: Mode) {
  if (mode === 'queue') return Users;
  if (mode === 'specialists') return Stethoscope;
  return CalendarDays;
}

export function HospitalRecordsPage({ mode, title, subtitle }: { mode: Mode; title: string; subtitle: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState(filterOptions[mode][0]);
  const Icon = iconForMode(mode);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const response = mode === 'queue' ? await listHospitalPatients() : mode === 'specialists' ? await listHospitalSpecialists() : await listHospitalDepartments();
      const records = listItems<Row>(response as { items?: Row[] } | Row[]);
      setRows(mode === 'departments' ? records.map(normalizeDepartment) : records);
    } catch (err) {
      setRows([]);
      setError(err instanceof Error ? err.message : 'Unable to load hospital records.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [mode]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => matchesFilter(mode, row, filter)).filter((row) => !needle || rowText(row).includes(needle));
  }, [filter, mode, query, rows]);

  return (
    <main className="mx-auto grid max-w-7xl gap-4 p-4 md:p-6">
      <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-emerald-700">Hospital workspace</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 md:text-3xl">{title}</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">{subtitle}</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_220px] md:min-w-[520px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search records" className="min-h-11 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-3 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" />
          </label>
          <select value={filter} onChange={(event) => setFilter(event.target.value)} className="min-h-11 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100">
            {filterOptions[mode].map((item) => <option key={item}>{item}</option>)}
          </select>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="flex gap-3"><AlertTriangle className="h-5 w-5" /> {error}</span>
            <button type="button" onClick={() => void load()} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-white px-3 py-2 font-bold ring-1 ring-amber-200"><RefreshCcw className="h-4 w-4" /> Retry</button>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <div className="grid gap-3">{[1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-lg bg-slate-100" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center rounded-lg border border-dashed border-slate-200 bg-white py-16 text-center">
          <Icon className="mb-3 h-10 w-10 text-slate-300" />
          <p className="text-sm font-bold text-slate-700">{emptyCopy[mode].title}</p>
          <p className="mt-1 text-sm text-slate-500">{emptyCopy[mode].body}</p>
        </div>
      ) : mode === 'queue' ? (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="hidden grid-cols-[1.2fr_1fr_.8fr_.8fr_.9fr_.8fr] gap-3 border-b border-slate-100 px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500 lg:grid">
            <span>Patient</span><span>Ticket</span><span>Urgency</span><span>Department</span><span>Doctor</span><span>Status</span>
          </div>
          <div className="divide-y divide-slate-100">
            {(filtered as HospitalPatient[]).map((item) => (
              <article key={item.id} className="grid gap-3 p-4 lg:grid-cols-[1.2fr_1fr_.8fr_.8fr_.9fr_.8fr] lg:items-center">
                <div><p className="font-bold text-slate-900">{item.patient_name}</p><p className="text-sm text-slate-500">{item.card_number ?? 'No card number'}</p></div>
                <div><p className="font-mono text-sm font-bold text-slate-900">{item.ticket_number}</p><p className="text-xs text-slate-500">{formatDate(item.arrival_time)}</p></div>
                <Badge value={item.urgency} />
                <span className="text-sm text-slate-700">{item.department ?? item.required_specialty ?? 'Unassigned'}</span>
                <span className="text-sm text-slate-700">{item.assigned_doctor}</span>
                <div className="flex flex-wrap gap-2"><Badge value={item.assignment_status} /><Badge value={item.queue_status} /></div>
              </article>
            ))}
          </div>
        </div>
      ) : mode === 'specialists' ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(filtered as HospitalSpecialist[]).map((item) => (
            <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3"><div><p className="text-lg font-bold text-slate-950">{item.full_name}</p><p className="text-sm text-slate-500">{item.title} · {item.specialty ?? 'General'}</p></div><Badge value={item.availability} /></div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm"><div><dt className="text-slate-500">Department</dt><dd className="font-bold text-slate-900">{item.department}</dd></div><div><dt className="text-slate-500">Today</dt><dd className="font-bold text-slate-900">{item.appointments_today}/{item.maximum_capacity}</dd></div><div><dt className="text-slate-500">Next slot</dt><dd className="font-bold text-slate-900">{formatDate(item.next_available_slot)}</dd></div><div><dt className="text-slate-500">License</dt><dd><Badge value={item.license_status} /></dd></div></dl>
            </article>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {(filtered as HospitalDepartment[]).map((item) => (
            <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3"><div><p className="text-lg font-bold text-slate-950">{item.name}</p><p className="text-sm text-slate-500">{item.description ?? 'Department operations'}</p></div><Badge value={item.capacity_status} /></div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4"><div><dt className="text-slate-500">Doctors</dt><dd className="font-bold text-slate-900">{item.available_doctors}/{item.total_doctors}</dd></div><div><dt className="text-slate-500">Nurses</dt><dd className="font-bold text-slate-900">{item.nurses_on_duty}</dd></div><div><dt className="text-slate-500">Waiting</dt><dd className="font-bold text-slate-900">{item.patients_waiting}</dd></div><div><dt className="text-slate-500">Today</dt><dd className="font-bold text-slate-900">{item.appointments_today}</dd></div></dl>
              {(() => {
                const availableDoctors = Array.isArray(item.available_doctors_list) ? item.available_doctors_list : [];
                return availableDoctors.length > 0 ? (
                  <div className="mt-4 space-y-2">
                    {availableDoctors.slice(0, 3).map((doctor) => (
                      <div key={doctor.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                        <span className="font-bold text-slate-800">{doctor.full_name}</span>
                        <Badge value={doctor.availability} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-slate-500">No doctors currently available in this department.</p>
                );
              })()}
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
