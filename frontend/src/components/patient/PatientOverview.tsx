'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, Calendar, CreditCard, Lightbulb, Ticket } from 'lucide-react';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { EmptyState } from '@/components/shared/EmptyState';
import { StatCard } from '@/components/shared/StatCard';
import { api } from '@/lib/auth';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

type CurrentUser = { first_name?: string; last_name?: string; full_name?: string; card_number?: string };
type PatientDashboard = {
  stats?: {
    active_tickets?: string | number;
    next_appointment?: string;
    queue_position?: string | number;
    health_card_status?: string;
  };
  activity?: { id?: string; title?: string; body?: string; created_at?: string }[];
  health_tip?: { title?: string; body?: string } | null;
};

export function PatientOverview() {
  const [mood, setMood] = useState('Good');
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [dashboard, setDashboard] = useState<PatientDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadDashboard() {
      try {
        const [userResult, dashboardResult] = await Promise.allSettled([
          api.get('/api/v1/auth/patient/me'),
          api.get('/api/v1/patient/dashboard'),
        ]);
        if (cancelled) return;
        setCurrentUser(userResult.status === 'fulfilled' ? (userResult.value as CurrentUser) : null);
        setDashboard(dashboardResult.status === 'fulfilled' ? (dashboardResult.value as PatientDashboard) : null);
      } catch (error) {
        console.error(error);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadDashboard();
    return () => {
      cancelled = true;
    };
  }, []);

  const firstName = currentUser?.first_name ?? currentUser?.full_name?.split(' ')[0] ?? '';
  const stats = dashboard?.stats;
  const activity = dashboard?.activity ?? [];

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl bg-gradient-to-r from-[#0b5d4b] to-[#073d33] p-6 text-white shadow-sm">
          {isLoading ? <div className="h-9 w-64 animate-pulse rounded bg-white/20" /> : <h2 className="font-display text-3xl">Welcome back, {firstName}</h2>}
          <p className="mt-1 text-blue-50">How are you feeling today?</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {['Good', 'Okay', 'Not well'].map((item) => (
              <button key={item} onClick={() => setMood(item)} className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${mood === item ? 'bg-white text-[#0b5d4b]' : 'bg-white/10 text-white hover:bg-white/20'}`}>
                {item}
              </button>
            ))}
          </div>
          {mood === 'Not well' ? (
            <Link href="/dashboard/chat" className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-[#0b5d4b]">
              Start a symptom check
              <Activity className="h-4 w-4" />
            </Link>
          ) : null}
        </section>
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Link href="/dashboard/queue"><StatCard title="Active Tickets" value={isLoading ? '—' : String(stats?.active_tickets ?? '—')} tone="amber" icon={Ticket} /></Link>
          <StatCard title="Next Appointment" value={isLoading ? '—' : stats?.next_appointment ?? '—'} tone="sky" icon={Calendar} />
          <Link href="/dashboard/queue"><StatCard title="Queue Position" value={isLoading ? '—' : String(stats?.queue_position ?? '—')} tone="sky" icon={Activity} /></Link>
          <Link href="/dashboard/card"><StatCard title="Health Card" value={isLoading ? '—' : stats?.health_card_status ?? currentUser?.card_number ?? '—'} tone="slate" icon={CreditCard} /></Link>
        </section>
        <section className="grid gap-5 xl:grid-cols-[1fr_0.45fr]">
          <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-slate-900">Recent Activity</h3>
            {isLoading ? (
              <div className="mt-4 space-y-3">
                {[1, 2, 3].map((item) => <div key={item} className="h-16 animate-pulse rounded-xl bg-slate-100" />)}
              </div>
            ) : activity.length === 0 ? (
              <div className="mt-4"><EmptyState title="No recent activity" body="Your recent visits, tickets, and updates will appear here." /></div>
            ) : (
              <div className="mt-4 space-y-3">
                {activity.map((item, index) => (
                  <div key={item.id ?? index} className="flex items-start gap-3 rounded-xl border border-slate-100 p-3">
                    <span className="mt-1 h-2 w-2 rounded-full bg-[#0b5d4b]" />
                    <div>
                      <p className="text-sm text-slate-700">{item.title ?? item.body}</p>
                      {item.created_at ? <p className="text-xs text-slate-400">{item.created_at}</p> : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>
          <article className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-[#0b5d4b]" />
              <h3 className="font-semibold text-slate-900">Health Tip</h3>
            </div>
            {dashboard?.health_tip ? (
              <p className="mt-3 text-sm leading-6 text-slate-600">{dashboard.health_tip.body ?? dashboard.health_tip.title}</p>
            ) : (
              <p className="mt-3 text-sm leading-6 text-slate-500">No health tip available</p>
            )}
          </article>
        </section>
      </div>
    </DashboardShell>
  );
}
