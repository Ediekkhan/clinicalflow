'use client';

import { useMemo, useState } from 'react';
import { Ban, CalendarClock, GripVertical, Lock, Send } from 'lucide-react';
import { demoSlots } from '@/lib/demo-data';
import type { ProviderSlot } from '@/lib/types';
import { lockSlot } from '@/lib/api';
import { cn } from '@/lib/utils';

const providerOrder = ['Dr. Ekanem', 'Dr. Balogun', 'Dr. Udo'];

export function AppointmentScheduler() {
  const [slots, setSlots] = useState<ProviderSlot[]>(demoSlots);
  const [draggedSlot, setDraggedSlot] = useState<string | null>(null);

  const grouped = useMemo(
    () =>
      providerOrder.map((provider) => ({
        provider,
        slots: slots.filter((slot) => slot.provider_name === provider),
      })),
    [slots],
  );

  async function toggleLock(slot: ProviderSlot) {
    setSlots((current) =>
      current.map((item) =>
        item.id === slot.id
          ? {
              ...item,
              is_locked: !item.is_locked,
              lock_reason: slot.is_locked ? null : 'Emergency period blocked by desk',
            }
          : item,
      ),
    );
    try {
      await lockSlot(slot.id, !slot.is_locked, slot.is_locked ? undefined : 'Emergency period blocked by desk');
    } catch {
      // Leave the local state visible; the queue network toast handles sync state elsewhere.
    }
  }

  function moveDragged(targetSlotId: string) {
    if (!draggedSlot || draggedSlot === targetSlotId) return;
    setSlots((current) => {
      const source = current.find((slot) => slot.id === draggedSlot);
      const target = current.find((slot) => slot.id === targetSlotId);
      if (!source || !target) return current;
      return current.map((slot) => {
        if (slot.id === source.id) return { ...slot, starts_at: target.starts_at, ends_at: target.ends_at };
        if (slot.id === target.id) return { ...slot, starts_at: source.starts_at, ends_at: source.ends_at };
        return slot;
      });
    });
    setDraggedSlot(null);
  }

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Master Scheduler</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Provider calendar grid</h1>
        </div>
        <button className="touch-target inline-flex items-center gap-2 bg-emerald-600 text-white hover:bg-emerald-700">
          <Send className="h-4 w-4" />
          Send patient updates
        </button>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {grouped.map((providerGroup) => (
          <section key={providerGroup.provider} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="mb-3 px-1">
              <p className="text-sm font-medium uppercase tracking-wider text-slate-500">{providerGroup.provider}</p>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">{providerGroup.slots[0]?.specialty}</h2>
            </div>
            <div className="grid gap-2">
              {providerGroup.slots.map((slot) => (
                <article
                  key={slot.id}
                  draggable={!slot.is_locked}
                  onDragStart={() => setDraggedSlot(slot.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => moveDragged(slot.id)}
                  className={cn(
                    'data-row flex min-h-20 items-center justify-between gap-3 rounded-lg border',
                    slot.is_locked ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-slate-200 bg-slate-50 text-slate-900',
                  )}
                >
                  <div className="flex items-center gap-3">
                    {slot.is_locked ? <Ban className="h-5 w-5" /> : <GripVertical className="h-5 w-5 text-slate-400" />}
                    <span>
                      <span className="block font-mono font-bold">
                        {new Intl.DateTimeFormat('en-NG', { hour: 'numeric', minute: '2-digit' }).format(new Date(slot.starts_at))}
                      </span>
                      <span className="block text-sm">{slot.room_label}</span>
                      {slot.lock_reason ? <span className="block text-sm font-medium">{slot.lock_reason}</span> : null}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleLock(slot)}
                    className="rounded-lg bg-white p-3 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100"
                    aria-label={slot.is_locked ? 'Unlock slot' : 'Lock slot'}
                  >
                    <Lock className="h-4 w-4" />
                  </button>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
        <CalendarClock className="mr-2 inline h-5 w-5" />
        Dragging a slot locally simulates staff overrides. Locking a slot calls the shared appointment API and broadcasts calendar changes to dashboards.
      </div>
    </section>
  );
}

