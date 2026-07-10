'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bell, Calendar, ClipboardList, FileText, FlaskConical, PackageCheck, Users } from 'lucide-react';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { Badge } from '@/components/shared/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { StatCard } from '@/components/shared/StatCard';
import { api } from '@/lib/auth';
import { dashboardEntities, type EntityKey } from '@/lib/dashboard-data';

export type View =
  | 'overview'
  | 'queue'
  | 'people'
  | 'appointments'
  | 'analytics'
  | 'notifications'
  | 'settings'
  | 'schedule'
  | 'notes'
  | 'earnings'
  | 'messages'
  | 'prescriptions'
  | 'inventory'
  | 'patients'
  | 'deliveries'
  | 'requests'
  | 'results'
  | 'collections'
  | 'visits'
  | 'vitals'
  | 'care-plans'
  | 'authorizations'
  | 'claims'
  | 'members'
  | 'facilities'
  | 'utilization'
  | 'payments'
  | 'equipment'
  | 'reports'
  | 'surveillance'
  | 'departments';

type EntityDashboardProps = {
  entity: EntityKey;
  view: View;
  title?: string;
  subtitle?: string;
};

type ApiRecord = Record<string, unknown>;
type ApiStat = { title?: string; label?: string; value?: ReactNode; sub?: string; description?: string; tone?: 'amber' | 'rose' | 'sky' | 'slate' | 'violet'; href?: string };
type ApiPayload = {
  identity?: { name?: string; full_name?: string; subtitle?: string; specialty?: string; location?: string; badge?: string; card_number?: string; initials?: string };
  stats?: ApiStat[];
  activity?: ApiRecord[];
  items?: ApiRecord[];
  rows?: ApiRecord[];
  notifications?: ApiRecord[];
  columns?: string[];
  chartData?: ApiRecord[];
};

const viewTitles: Record<View, string> = {
  overview: 'Overview',
  queue: 'Queue',
  people: 'People',
  appointments: 'Appointments',
  analytics: 'Analytics',
  notifications: 'Notifications',
  settings: 'Settings',
  schedule: 'Schedule',
  notes: 'Patient Records',
  earnings: 'Earnings',
  messages: 'Messages',
  prescriptions: 'Prescriptions',
  inventory: 'Inventory',
  patients: 'Patients',
  deliveries: 'Deliveries',
  requests: 'Test Requests',
  results: 'Results',
  collections: 'Collections',
  visits: 'Home Visits',
  vitals: 'Vitals',
  'care-plans': 'Care Plans',
  authorizations: 'Authorizations',
  claims: 'Claims',
  members: 'Members',
  facilities: 'Facilities',
  utilization: 'Utilization',
  payments: 'Payments',
  equipment: 'Equipment',
  reports: 'Reports',
  surveillance: 'Surveillance',
  departments: 'Departments',
};

const emptyCopy: Partial<Record<View, { title: string; body: string }>> = {
  patients: { title: 'No patients assigned yet', body: 'Assigned patients will appear here once the API returns them.' },
  people: { title: 'No users available', body: 'Users will appear here after they are loaded from the API.' },
  appointments: { title: 'No appointments scheduled', body: 'Scheduled visits will appear here when available.' },
  notifications: { title: "You're all caught up", body: 'New notifications will appear here in real time.' },
  prescriptions: { title: 'No pending prescriptions', body: 'Prescription requests will appear here when available.' },
  requests: { title: 'No test requests', body: 'Lab requests will appear here when available.' },
  claims: { title: 'No claims to review', body: 'Claims from the API will appear here.' },
  members: { title: 'No members enrolled yet', body: 'Member records will appear here once available.' },
  results: { title: 'No results available', body: 'Released results will appear here.' },
};

function endpointFor(entity: EntityKey, view: View) {
  const resource = view === 'overview' ? 'dashboard' : view;
  return `/api/v1/${entity}/${resource}`;
}

function getItems(payload: ApiPayload | null, view: View) {
  if (!payload) return [];
  if (view === 'notifications') return payload.notifications ?? payload.items ?? payload.rows ?? [];
  return payload.items ?? payload.rows ?? [];
}

function getString(record: ApiRecord, keys: string[], fallback = '') {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) return value;
    if (typeof value === 'number') return String(value);
  }
  return fallback;
}

function getStatusTone(value: string) {
  const normalized = value.toUpperCase();
  if (normalized.includes('CRITICAL') || normalized.includes('CANCELLED') || normalized.includes('DENIED')) return 'rose' as const;
  if (normalized.includes('URGENT') || normalized.includes('PENDING') || normalized.includes('MISSED')) return 'amber' as const;
  if (normalized.includes('COMPLETED') || normalized.includes('DONE') || normalized.includes('APPROVED') || normalized.includes('ACTIVE')) return 'success' as const;
  return 'slate' as const;
}

function PageTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <header className="mb-9 flex flex-col justify-between gap-5 md:flex-row md:items-start">
      <div>
        <h1 className="text-4xl font-black tracking-normal text-[#020b22]">{title}</h1>
        {subtitle ? <p className="mt-3 text-xl text-[#526783]">{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}

function SkeletonCards() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((item) => (
        <div key={item} className="h-20 animate-pulse rounded-xl bg-slate-100" />
      ))}
    </div>
  );
}

function StatGrid({ stats, isLoading }: { stats: ApiStat[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((item) => (
          <div key={item} className="h-36 animate-pulse rounded-[22px] bg-slate-100" />
        ))}
      </div>
    );
  }

  if (!stats.length) return null;

  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat, index) => {
        const card = (
          <StatCard
            title={stat.title ?? stat.label ?? 'Metric'}
            value={stat.value == null || stat.value === '' ? '—' : String(stat.value)}
            sub={stat.sub ?? stat.description}
            tone={stat.tone ?? 'slate'}
          />
        );
        return stat.href ? (
          <Link key={`${stat.title ?? stat.label ?? 'metric'}-${index}`} href={stat.href} className="block rounded-[22px] transition hover:-translate-y-0.5 hover:shadow-lg">
            {card}
          </Link>
        ) : (
          <div key={`${stat.title ?? stat.label ?? 'metric'}-${index}`}>{card}</div>
        );
      })}
    </div>
  );
}

function RecordList({ items, view, isLoading, onNotificationClick }: { items: ApiRecord[]; view: View; isLoading: boolean; onNotificationClick?: (record: ApiRecord) => void }) {
  if (isLoading) return <SkeletonCards />;

  if (!items.length) {
    const copy = emptyCopy[view] ?? { title: 'No records available', body: 'Records will appear here once the API returns data.' };
    const icon = view === 'appointments' ? Calendar : view === 'notifications' ? Bell : view === 'prescriptions' ? ClipboardList : view === 'requests' || view === 'results' ? FlaskConical : view === 'patients' || view === 'members' || view === 'queue' ? Users : PackageCheck;
    return <EmptyState icon={icon} title={copy.title} body={copy.body} />;
  }

  return (
    <div className="grid gap-4">
      {items.map((item, index) => {
        const title = getString(item, ['title', 'name', 'full_name', 'patient_name', 'facility_name', 'ticket_number'], 'Record');
        const body = getString(item, ['body', 'description', 'summary', 'condition', 'matched_condition_name', 'specialty', 'status']);
        const meta = getString(item, ['meta', 'subtitle', 'created_at', 'updated_at', 'scheduled_at', 'appointment_slot']);
        const status = getString(item, ['urgency', 'urgency_level', 'status', 'queue_status', 'is_read']);
        const isNotification = view === 'notifications';

        return (
          <button
            key={getString(item, ['id'], `${view}-${index}`)}
            type="button"
            onClick={isNotification ? () => onNotificationClick?.(item) : undefined}
            className="w-full rounded-2xl border border-slate-100 bg-white p-5 text-left shadow-sm transition hover:border-[#2563EB]/40 hover:shadow-md"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-slate-900">{title}</h3>
                {body ? <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p> : null}
                {meta ? <p className="mt-2 text-xs font-semibold text-slate-400">{meta}</p> : null}
              </div>
              {status ? <Badge tone={getStatusTone(status)}>{status}</Badge> : null}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function SettingsPanel({ isLoading }: { isLoading: boolean }) {
  if (isLoading) return <SkeletonCards />;
  return <EmptyState icon={FileText} title="No profile fields available" body="Profile settings will appear when the API returns editable fields." />;
}

function ChartPlaceholder({ chartData, isLoading }: { chartData: ApiRecord[]; isLoading: boolean }) {
  if (isLoading) return <div className="h-48 animate-pulse rounded-xl bg-slate-100" />;
  if (!chartData.length) {
    return (
      <div className="flex h-48 items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white">
        <p className="text-sm text-slate-400">No data yet</p>
      </div>
    );
  }
  return <RecordList items={chartData} view="analytics" isLoading={false} />;
}

export function EntityDashboard({ entity: entityKey, view, title, subtitle }: EntityDashboardProps) {
  const entity = dashboardEntities[entityKey];
  const router = useRouter();
  const [payload, setPayload] = useState<ApiPayload | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);

    async function load() {
      try {
        const data = await api.get(endpointFor(entityKey, view));
        if (!cancelled) setPayload((data ?? {}) as ApiPayload);
      } catch (error) {
        console.error(error);
        if (!cancelled) setPayload({});
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [entityKey, view]);

  const identity = useMemo(() => {
    const source = payload?.identity;
    if (!source) return entity.identity;
    return {
      ...entity.identity,
      name: source.name ?? source.full_name ?? entity.identity.name,
      subtitle: source.subtitle ?? source.specialty ?? source.location ?? entity.identity.subtitle,
      badge: source.badge ?? source.card_number,
      initials: source.initials ?? entity.identity.initials,
    };
  }, [entity.identity, payload?.identity]);

  const items = getItems(payload, view);

  function handleNotificationClick(notification: ApiRecord) {
    const type = getString(notification, ['type']);
    const id = getString(notification, ['id']);

    if (id) {
      setPayload((current) => {
        if (!current) return current;
        const update = (record: ApiRecord) => (record.id === id ? { ...record, is_read: true } : record);
        return {
          ...current,
          notifications: current.notifications?.map(update),
          items: current.items?.map(update),
          rows: current.rows?.map(update),
        };
      });
    }

    const patientRoutes: Record<string, string> = {
      NEW_TICKET: '/dashboard/queue',
      QUEUE_UPDATE: '/dashboard/queue',
      BEING_SEEN: '/dashboard/queue',
      APPOINTMENT_CONFIRMED: '/dashboard/appointments',
      APPOINTMENT_CANCELLED: '/dashboard/appointments',
      APPOINTMENT_REMINDER: '/dashboard/appointments',
      TRIAGE_RESULT: '/dashboard/chat',
      PRESCRIPTION_READY: '/dashboard/history',
      LAB_RESULT: '/dashboard/history',
    };

    const portalRoutes: Record<EntityKey, Record<string, string>> = {
      patient: patientRoutes,
      specialist: { NEW_TICKET: '/specialist/patients', QUEUE_UPDATE: '/specialist/patients', APPOINTMENT_CONFIRMED: '/specialist/schedule', APPOINTMENT_REMINDER: '/specialist/schedule', LAB_RESULT: '/specialist/patients' },
      hospital: { NEW_TICKET: '/hospital/queue', QUEUE_UPDATE: '/hospital/queue', BEING_SEEN: '/hospital/queue', APPOINTMENT_CONFIRMED: '/hospital/appointments', APPOINTMENT_CANCELLED: '/hospital/appointments' },
      pharmacy: { PRESCRIPTION_READY: '/pharmacy/prescriptions', QUEUE_UPDATE: '/pharmacy/prescriptions' },
      lab: { NEW_TICKET: '/lab/requests', LAB_RESULT: '/lab/results' },
      clinic: { NEW_TICKET: '/clinic/queue', QUEUE_UPDATE: '/clinic/queue', APPOINTMENT_CONFIRMED: '/clinic/appointments', APPOINTMENT_CANCELLED: '/clinic/appointments' },
      nurse: { NEW_TICKET: '/nurse/queue', QUEUE_UPDATE: '/nurse/queue', APPOINTMENT_REMINDER: '/nurse/visits', BEING_SEEN: '/nurse/queue' },
      hmo: { NEW_TICKET: '/hmo/claims', QUEUE_UPDATE: '/hmo/authorizations', APPOINTMENT_CONFIRMED: '/hmo/authorizations' },
      moh: {},
      admin: {},
    };

    const route = portalRoutes[entityKey][type];
    if (route) router.push(route);
  }

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={identity}>
      <PageTitle title={title ?? viewTitles[view]} subtitle={subtitle} />
      <div className="grid gap-6">
        {view === 'overview' ? (
          <>
            <StatGrid stats={payload?.stats ?? []} isLoading={isLoading} />
            <RecordList items={payload?.activity ?? []} view={view} isLoading={isLoading} />
          </>
        ) : view === 'analytics' || view === 'utilization' || view === 'reports' || view === 'surveillance' ? (
          <ChartPlaceholder chartData={payload?.chartData ?? items} isLoading={isLoading} />
        ) : view === 'settings' ? (
          <SettingsPanel isLoading={isLoading} />
        ) : (
          <RecordList items={items} view={view} isLoading={isLoading} onNotificationClick={handleNotificationClick} />
        )}
      </div>
    </DashboardShell>
  );
}
