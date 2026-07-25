'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Ban, CalendarClock, GripVertical, Lock, LogIn, Radio, RefreshCcw } from 'lucide-react';
import type { Appointment, ProviderSlot } from '@/lib/types';
import { ApiError, listHospitalAppointments, listHospitalSlots, lockSlot, rescheduleAppointment } from '@/lib/api';
import { cn } from '@/lib/utils';

export function AppointmentScheduler() {
  const [slots, setSlots] = useState<ProviderSlot[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [draggedAppointment, setDraggedAppointment] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);

  async function loadSchedule() {
    setIsLoading(true);
    setError(null);
    setAccessDenied(false);
    const results = await Promise.allSettled([listHospitalSlots(), listHospitalAppointments()]);
    const slotResult = results[0];
    const appointmentResult = results[1];
    if (slotResult.status === 'fulfilled') setSlots(slotResult.value);
    else setSlots([]);
    if (appointmentResult.status === 'fulfilled') setAppointments(appointmentResult.value);
    else setAppointments([]);
    const failures = results.filter((result) => result.status === 'rejected') as PromiseRejectedResult[];
    const forbidden = failures.some((failure) => failure.reason instanceof ApiError && failure.reason.status === 403);
    if (forbidden) {
      setAccessDenied(true);
      setError('You do not have access to this hospital appointment workspace.');
    } else if (failures.length > 0) {
      setError('Your session may have expired or the appointment service is unavailable.');
    }
    setIsLoading(false);
  }

  useEffect(() => {
    void loadSchedule();
  }, []);
  const grouped = useMemo(() => {
    const providers = Array.from(new Set(slots.map((slot) => slot.provider_name).filter(Boolean)));
    return providers.map((provider) => ({
      provider,
      slots: slots.filter((slot) => slot.provider_name === provider),
    }));
  }, [slots]);

  const appointmentBySlot = useMemo(() => new Map(appointments.filter((item) => item.status === 'BOOKED').map((item) => [item.slot_id, item])), [appointments]);

  async function toggleLock(slot: ProviderSlot) {
    setSlots((current) =>
      current.map((item) =>
        item.id === slot.id
          ? {
              ...item,
              is_locked: !item.is_locked,
              lock_reason: slot.is_locked ? null : 'Unavailable',
            }
          : item,
      ),
    );
    try {
      await lockSlot(slot.id, !slot.is_locked, slot.is_locked ? undefined : 'Unavailable');
      setError(null);
    } catch {
      setError('Unable to update this slot. Please retry.');
      setSlots((current) => current.map((item) => item.id === slot.id ? slot : item));
    }
  }

  async function moveDragged(targetSlotId: string) {
    if (!draggedAppointment) return;
    const appointment = appointments.find((item) => item.id === draggedAppointment);
    const target = slots.find((slot) => slot.id === targetSlotId);
    if (!appointment || !target || target.is_locked || target.is_booked || appointment.slot_id === targetSlotId) return;
    const previousSlotId = appointment.slot_id;
    setSlots((current) => {
      return current.map((slot) => slot.id === previousSlotId ? { ...slot, is_booked: false } : slot.id === targetSlotId ? { ...slot, is_booked: true } : slot);
    });
    setAppointments((current) => current.map((item) => item.id === appointment.id ? { ...item, slot_id: targetSlotId, starts_at: target.starts_at, ends_at: target.ends_at, provider_name: target.provider_name, specialty: target.specialty, room_label: target.room_label } : item));
    setDraggedAppointment(null);
    try {
      const updated = await rescheduleAppointment(appointment.id, targetSlotId);
      setAppointments((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch {
      setSlots((current) => current.map((slot) => slot.id === previousSlotId ? { ...slot, is_booked: true } : slot.id === targetSlotId ? { ...slot, is_booked: false } : slot));
      setAppointments((current) => current.map((item) => item.id === appointment.id ? appointment : item));
      setError('Unable to reschedule this appointment. Please retry.');
    }
  }

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Master Scheduler</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Provider calendar grid</h1>
        </div>
        <span className="touch-target inline-flex items-center gap-2 bg-emerald-50 text-emerald-700"><Radio className="h-4 w-4" /> Patient updates automatic</span>
      </div>
      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="font-bold">Unable to load hospital appointments</p>
                <p>{error}</p>
              </div>
            </div>
            <div className="flex gap-2">
              {!accessDenied ? (
                <button type="button" onClick={() => void loadSchedule()} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-white px-3 py-2 font-bold text-amber-900 ring-1 ring-amber-200 hover:bg-amber-100">
                  <RefreshCcw className="h-4 w-4" /> Retry
                </button>
              ) : null}
              <a href="/hospital/login?reason=session-expired" className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-emerald-900 px-3 py-2 font-bold text-white hover:bg-emerald-800">
                <LogIn className="h-4 w-4" /> Sign in again
              </a>
            </div>
          </div>
        </div>
      ) : null}
      {isLoading ? (
        <div className="grid gap-3 lg:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-72 animate-pulse rounded-lg bg-slate-100" />)}</div>
      ) : grouped.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-500">No appointments scheduled yet</div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-3">
          {grouped.map((providerGroup) => (
            <section key={providerGroup.provider} className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="mb-3 px-1">
                <p className="text-sm font-medium uppercase tracking-wider text-slate-500">{providerGroup.provider}</p>
                <h2 className="text-2xl font-bold tracking-tight text-slate-900">{providerGroup.slots[0]?.specialty}</h2>
              </div>
              <div className="grid gap-2">
                {providerGroup.slots.map((slot) => {
                  const appointment = appointmentBySlot.get(slot.id);
                  return <article
                    key={slot.id}
                    draggable={Boolean(appointment)}
                    onDragStart={() => appointment && setDraggedAppointment(appointment.id)}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={() => void moveDragged(slot.id)}
                    className={cn(
                      'data-row flex min-h-20 items-center justify-between gap-3 rounded-lg border',
                      slot.is_locked ? 'border-rose-200 bg-rose-50 text-rose-700' : appointment ? 'cursor-grab border-blue-200 bg-blue-50 text-blue-900' : 'border-slate-200 bg-slate-50 text-slate-900',
                    )}
                  >
                    <div className="flex items-center gap-3">
                      {slot.is_locked ? <Ban className="h-5 w-5" /> : appointment ? <GripVertical className="h-5 w-5 text-blue-500" /> : <CalendarClock className="h-5 w-5 text-slate-400" />}
                      <span>
                        <span className="block font-mono font-bold">
                          {new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(slot.starts_at))}
                        </span>
                        <span className="block text-sm">{slot.room_label}</span>
                        {appointment ? <span className="block text-sm font-bold">Booked · {appointment.customer_phone}</span> : null}
                        {slot.lock_reason ? <span className="block text-sm font-medium">{slot.lock_reason}</span> : null}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleLock(slot)}
                      disabled={slot.is_booked}
                      className="rounded-lg bg-white p-3 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100"
                      aria-label={slot.is_locked ? 'Unlock slot' : 'Lock slot'}
                    >
                      <Lock className="h-4 w-4" />
                    </button>
                  </article>;
                })}
              </div>
            </section>
          ))}
        </div>
      )}
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
        <CalendarClock className="mr-2 inline h-5 w-5" />
        Hospital appointments and provider slots are scoped to verified staff at this hospital.
      </div>
    </section>
  );
}
