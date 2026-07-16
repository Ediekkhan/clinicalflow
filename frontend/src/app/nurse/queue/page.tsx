'use client';

import { Activity, AlertTriangle, Clock3, Users } from 'lucide-react';
import { NetworkToast } from '@/components/NetworkToast';
import { TriageKanban } from '@/components/TriageKanban';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { StatCard } from '@/components/shared/StatCard';
import { useTriageQueue } from '@/hooks/useTriageQueue';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.nurse;

export default function NurseQueuePage() {
  const { tickets, grouped, networkMode, pendingActions, forceOvertake, setStatus } = useTriageQueue();
  const active = tickets.filter((ticket) => ticket.queue_status !== 'RESOLVED');

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <NetworkToast mode={networkMode} />
      <div className="grid gap-6 pt-10">
        <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-bold uppercase tracking-wider text-blue-600">Live Triage Command Centre</p>
            <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-900">Nurse queue</h1>
            <p className="mt-2 text-sm text-slate-600">Real-time clinical queue with optimistic actions and forced overtake escalation.</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600">
            Last synchronized · {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard title="Active patients" value={String(active.length)} sub="Across all triage lanes" tone="sky" />
          <StatCard title="Critical" value={String(grouped.CRITICAL.length)} sub="Immediate attention" tone="rose" />
          <StatCard title="Urgent" value={String(grouped.URGENT.length)} sub="Delayed care risk" tone="amber" />
          <StatCard title="Pending sync" value={String(pendingActions.length)} sub={networkMode === 'connected' ? 'Clinic stream online' : 'Stored on this device'} tone="slate" />
        </section>

        {active.length === 0 ? (
          <section className="grid min-h-80 place-items-center rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
            <div>
              <Users className="mx-auto h-12 w-12 text-slate-300" />
              <h2 className="mt-4 text-xl font-bold text-slate-900">Queue is clear</h2>
              <p className="mt-2 text-sm text-slate-500">New web, WhatsApp, and SMS tickets will appear here automatically.</p>
            </div>
          </section>
        ) : (
          <TriageKanban grouped={grouped} forceOvertake={forceOvertake} setStatus={setStatus} />
        )}

        <section className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 sm:grid-cols-3">
          <p className="inline-flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-rose-600" /> Forced overtake writes an audit event.</p>
          <p className="inline-flex items-center gap-2"><Activity className="h-4 w-4 text-blue-600" /> Queue updates arrive by WebSocket.</p>
          <p className="inline-flex items-center gap-2"><Clock3 className="h-4 w-4 text-amber-600" /> Offline actions sync after reconnect.</p>
        </section>
      </div>
    </DashboardShell>
  );
}
