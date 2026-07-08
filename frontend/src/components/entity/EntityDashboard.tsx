'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { CheckCircle2, Plus } from 'lucide-react';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { Badge } from '@/components/shared/Badge';
import { DataTable } from '@/components/shared/DataTable';
import { StatCard } from '@/components/shared/StatCard';
import { dashboardEntities, type EntityKey } from '@/lib/dashboard-data';

type View =
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

const people = ['Emeka Obi', 'Adaeze Chukwu', 'James Akpan', 'Ngozi Udo'];
const urgencyTone = { CRITICAL: 'critical', URGENT: 'urgent', ROUTINE: 'routine' } as const;

function PageTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
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

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-[22px] border border-[#dbe3ef] bg-white p-8 ${className}`}>{children}</section>;
}

function StatGrid({ stats, columns = 'xl:grid-cols-4' }: { stats: typeof dashboardEntities.hospital.stats; columns?: string }) {
  return (
    <div className={`grid gap-6 md:grid-cols-2 ${columns}`}>
      {stats.map(({ href, ...stat }) => {
        const card = <StatCard {...stat} />;
        if (!href) return <div key={stat.title}>{card}</div>;
        return (
          <Link
            key={stat.title}
            href={href}
            className="block rounded-[22px] transition hover:-translate-y-0.5 hover:shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2563EB] focus-visible:ring-offset-2"
          >
            {card}
          </Link>
        );
      })}
    </div>
  );
}

function Pill({ children, tone = 'routine' }: { children: React.ReactNode; tone?: 'critical' | 'urgent' | 'routine' | 'success' | 'slate' | 'violet' | 'amber' | 'rose' }) {
  return <Badge tone={tone}>{children}</Badge>;
}

function Progress({ value, color = 'bg-[#2563EB]' }: { value: number; color?: string }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
    </div>
  );
}

function RoleTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-hidden rounded-[22px] border border-[#dbe3ef] bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th key={column} className="px-7 py-5 text-left text-xs font-extrabold uppercase tracking-[0.12em] text-[#8a97b4]">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-slate-50/60">
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`} className={`px-7 py-5 text-base ${cellIndex === 0 ? 'font-black text-[#020b22]' : 'text-[#526783]'}`}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TextField({ label, value }: { label: string; value: string }) {
  return (
    <label className="block">
      <span className="text-sm font-extrabold text-[#526783]">{label}</span>
      <input readOnly value={value} className="mt-2 w-full rounded-xl border border-[#dbe3ef] bg-white px-4 py-3 text-lg outline-none" />
    </label>
  );
}

function MockChart({ labels = ['M', 'T', 'W', 'T', 'F', 'S', 'S'], className = '' }: { labels?: string[]; className?: string }) {
  return (
    <div className={`flex min-h-[230px] items-center justify-around pt-16 text-sm text-[#8a97b4] ${className}`}>
      {labels.map((label) => <span key={label}>{label}</span>)}
    </div>
  );
}

function MetricBars({ items }: { items: [string, number, string][] }) {
  return (
    <div className="space-y-5">
      {items.map(([label, value, color]) => (
        <div key={label}>
          <div className="mb-2 flex justify-between text-[#526783]">
            <span>{label}</span>
            <b className="text-[#020b22]">{value}%</b>
          </div>
          <Progress value={value} color={color} />
        </div>
      ))}
    </div>
  );
}

function SparkBars({ color, values }: { color: string; values: number[] }) {
  return (
    <div className="flex h-16 items-end gap-1">
      {values.map((height, index) => (
        <span key={`${height}-${index}`} className={`w-3 rounded-t ${color}`} style={{ height: `${height}%` }} />
      ))}
    </div>
  );
}

function GoogleMapEmbed({ title, query, caption, className = '' }: { title: string; query: string; caption?: string; className?: string }) {
  const src = `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
  const externalHref = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;

  return (
    <div className={`overflow-hidden rounded-[18px] border border-[#dbe3ef] bg-white ${className}`}>
      <iframe
        title={title}
        src={src}
        className="h-[275px] w-full border-0"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        allowFullScreen
      />
      <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm font-bold text-[#526783]">
        <span>{caption ?? title}</span>
        <Link href={externalHref} target="_blank" rel="noreferrer" className="shrink-0 text-[#2563EB] hover:text-[#1D4ED8]">
          Open in Google Maps {'->'}
        </Link>
      </div>
    </div>
  );
}

function DoctorDashboard({ view }: { view: View }) {
  if (view === 'queue' || view === 'patients') {
    return (
      <>
        <PageTitle title={view === 'queue' ? 'Patient Queue' : 'Patient Records'} subtitle={view === 'queue' ? 'Cardiology · Live view' : 'All patients assigned to you'} />
        {view === 'queue' ? (
          <div className="grid gap-6 xl:grid-cols-3">
            {[
              ['WAITING · 3', '#fff9e8', '#facc15', people.slice(1)],
              ['BEING SEEN · 1', '#eff6ff', '#93c5fd', ['Emeka Obi']],
              ['RESOLVED TODAY · 2', '#eff6ff', '#93c5fd', ['Abiodun Eze', 'Chidinma Okafor']],
            ].map(([label, bg, border, names]) => (
              <section key={String(label)} className="min-h-[494px] rounded-[18px] border p-6" style={{ background: String(bg), borderColor: String(border) }}>
                <p className="mb-5 text-sm font-extrabold uppercase tracking-[0.12em] text-[#526783]">{label}</p>
                <div className="space-y-4">
                  {(names as string[]).map((name, index) => (
                    <article key={name} className="rounded-[14px] bg-white p-5">
                      <div className="flex items-start justify-between gap-4">
                        <h3 className="font-extrabold text-[#020b22]">{name}</h3>
                        <Pill tone={index === 0 && label !== 'RESOLVED TODAY · 2' ? 'urgent' : 'routine'}>{index === 0 && label !== 'RESOLVED TODAY · 2' ? 'URGENT' : 'ROUTINE'}</Pill>
                      </div>
                      <p className="mt-4 font-mono text-sm text-[#8a97b4]">SV-00{index ? '398' : '412'}</p>
                      <p className="mt-2 text-[#526783]">{label === 'BEING SEEN · 1' ? 'Room 4' : label === 'RESOLVED TODAY · 2' ? 'Completed' : index ? '~58 min' : '~35 min'}</p>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <DataTable
            columns={['Name', 'Last Visit', 'Condition', 'Urgency', 'Actions']}
            rows={[
              ['Emeka Obi', 'Jun 20, 2026', 'Hypertensive crisis', 'URGENT', 'View Records'],
              ['Adaeze Chukwu', 'Jun 20, 2026', 'Chest pain, arm numbness', 'URGENT', 'View Records'],
              ['James Akpan', 'Jun 15, 2026', 'Atrial fibrillation follow-up', 'ROUTINE', 'View Records'],
              ['Ngozi Udo', 'Jun 10, 2026', 'Chest tightness', 'ROUTINE', 'View Records'],
            ]}
          />
        )}
      </>
    );
  }

  if (view === 'appointments') {
    return (
      <>
        <PageTitle title="Appointments" subtitle="Week of June 20, 2026" />
        <AppointmentList />
      </>
    );
  }

  if (view === 'schedule') {
    return (
      <>
        <PageTitle
          title="Schedule"
          subtitle="Week of June 20, 2026"
          action={<div className="flex gap-3"><button className="rounded-xl bg-[#2563EB] px-6 py-5 font-bold text-white">Available</button><button className="rounded-xl border border-[#dbe3ef] bg-white px-6 py-5 font-bold">Unavailable</button><button className="rounded-xl border border-[#dbe3ef] bg-white px-6 py-5 font-bold">Off Duty</button></div>}
        />
        <ScheduleGrid />
      </>
    );
  }

  if (view === 'earnings' || view === 'analytics') return <Analytics title="Analytics" subtitle="Performance summary · June 2026" doctor />;

  if (view === 'settings') {
    return (
      <>
        <PageTitle title="Settings" subtitle="Profile and preferences" />
        <SettingsRows rows={[['Specialty', 'Cardiology'], ['Experience', '12 years'], ['Languages', 'English, Efik'], ['Hours', '8:00 AM – 5:00 PM'], ['Reg. No.', 'NMC-00-44821']]} hero="Dr. Okon Bassey" sub="Cardiologist · Ibom Specialist Hospital" initials="OB" />
      </>
    );
  }

  return (
    <>
      <PageTitle title="Welcome back, Dr. Bassey" subtitle="Friday, 20 June 2026 · Cardiology Ward" />
      <StatGrid stats={[
        { title: 'Patients Today', value: '12', sub: '+3 from yesterday', tone: 'sky' },
        { title: 'Currently Seeing', value: 'Active ·', sub: 'Emeka Obi · Room 4', tone: 'sky' },
        { title: 'Appointments', value: '8', sub: '2 remaining', tone: 'slate' },
        { title: 'Avg. Consult', value: '24 min', sub: 'Within target', tone: 'slate' },
      ]} />
      <div className="mt-9 grid gap-6 xl:grid-cols-[1.6fr_0.95fr]">
        <Card>
          <h2 className="mb-6 text-xl font-black">Current Patient</h2>
          <div className="rounded-[14px] border border-blue-200 bg-blue-50 p-6">
            <div className="flex justify-between gap-4"><h3 className="text-xl font-black">Emeka Obi</h3><Pill tone="urgent">URGENT</Pill></div>
            <p className="mt-3 font-mono text-sm text-[#526783]">SV-AKS-2026-00389 · Room 4</p>
            <p className="mt-4 text-lg leading-7 text-[#334b68]">Hypertensive crisis, BP 180/110. History of cardiovascular disease. On Amlodipine 5mg.</p>
            <div className="mt-5 flex flex-wrap gap-3"><button className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Mark Resolved</button><button className="rounded-xl border border-amber-300 px-6 py-3 font-bold text-amber-600">Escalate</button><Link href="/specialist/notes" className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">Add Notes</Link></div>
          </div>
        </Card>
        <Card><h2 className="mb-6 text-xl font-black">Today's Schedule</h2><ScheduleList /></Card>
      </div>
    </>
  );
}

function HospitalDashboard({ view }: { view: View }) {
  if (view === 'queue') {
    return (
      <>
        <PageTitle title="Patient Queue" subtitle="All departments · 23 waiting" action={<div className="flex flex-wrap gap-3"><button className="rounded-xl border border-[#dbe3ef] bg-white px-6 py-3 font-bold">All Departments⌄</button><button className="rounded-xl border border-[#dbe3ef] bg-white px-6 py-3 font-bold">All Urgencies⌄</button><button className="rounded-xl border border-[#dbe3ef] bg-white px-6 py-3 font-bold">All Specialists⌄</button></div>} />
        <DataTable columns={['Patient', 'Dept', 'Urgency', 'Doctor', 'Room', 'Wait', 'Actions']} rows={[
          ['Bola Adeleke', 'Emergency', 'CRITICAL', 'Dr. Eze', 'ER-1', '5 min', 'Reassign'],
          ['Emeka Obi', 'Cardiology', 'URGENT', 'Dr. Okon', 'Room 4', '12 min', 'Reassign'],
          ['Adaeze Chukwu', 'Cardiology', 'URGENT', 'Dr. Okon', 'Room 4', '35 min', 'Reassign'],
          ['James Akpan', 'Cardiology', 'ROUTINE', 'Dr. Okon', 'Room 4', '58 min', 'Reassign'],
          ['Ngozi Udo', 'General', 'ROUTINE', 'Dr. Amara', 'Room 2', '40 min', 'Reassign'],
        ]} />
      </>
    );
  }

  if (view === 'people') {
    return (
      <>
        <PageTitle title="Specialists" subtitle="18 registered specialists" action={<Link href="/signup?type=specialist" className="rounded-xl bg-[#6157f5] px-7 py-5 font-extrabold text-white">+ Add Specialist</Link>} />
        <DataTable columns={['Name', 'Specialty', 'Status', 'Patients Today', 'Rating', 'Actions']} rows={[
          ['Dr. Okon Bassey', 'Cardiology', 'Available', 12, '★★★★★', 'Schedule'],
          ['Dr. Amara Nwodo', 'General Medicine', 'Available', 9, '★★★★★', 'Schedule'],
          ['Dr. Bello Eze', 'Emergency Medicine', 'Unavailable', 7, '★★★★☆', 'Schedule'],
          ['Dr. Fatima Aliyu', 'Pediatrics', 'Available', 11, '★★★★★', 'Schedule'],
          ['Dr. Chukwu Mazi', 'OB-GYN', 'Off Duty', 0, '★★★★★', 'Schedule'],
        ]} />
      </>
    );
  }

  if (view === 'appointments') return <><PageTitle title="Appointments" subtitle="Today · 34 scheduled" /><AppointmentList hospital /></>;
  if (view === 'departments') return <><PageTitle title="Departments" subtitle="6 active departments" /><DepartmentCards full /></>;
  if (view === 'analytics') return <Analytics title="Analytics" subtitle="Patient and performance insights" />;
  if (view === 'notifications') return <Notifications />;
  if (view === 'settings') return <><PageTitle title="Settings" subtitle="Hospital profile and configuration" /><SettingsRows rows={[['Hospital Name', 'Ibom Specialist Hospital'], ['Location', 'Uyo, Akwa Ibom State'], ['Registration', 'HOS-NIG-00-2218'], ['Total Beds', '120'], ['Emergency Line', '+234 803 000 1234'], ['SynaptiVerse Tier', 'Enterprise Partner']]} /></>;

  return (
    <>
      <PageTitle title="Hospital Overview" subtitle="Friday, 20 June 2026 · Live dashboard" />
      <StatGrid stats={dashboardEntities.hospital.stats} columns="xl:grid-cols-3" />
      <h2 className="mb-5 mt-9 text-xl font-black">Department Queue Status</h2>
      <DepartmentCards />
      <Card className="mt-9">
        <h2 className="mb-5 flex items-center gap-3 text-xl font-black"><span className="h-2.5 w-2.5 rounded-full bg-rose-500" />Recent Escalations</h2>
        {['Bola Adeleke · SV-00415|Hypertensive crisis · BP 185/115 · 5 min ago', 'Emeka Obi · SV-00389|Chest pain + diaphoresis · 12 min ago'].map((item) => {
          const [name, detail] = item.split('|');
          return <div key={item} className="mb-4 flex items-center justify-between rounded-[14px] border border-rose-200 bg-rose-50 p-5"><div><p className="font-black">{name}</p><p className="text-[#526783]">{detail}</p></div><Link href="/hospital/notifications" className="rounded-xl bg-rose-500 px-6 py-3 font-bold text-white">Respond</Link></div>;
        })}
      </Card>
    </>
  );
}

function PharmacyDashboard({ view }: { view: View }) {
  if (view === 'inventory') return <><PageTitle title="Inventory" subtitle="Drug stock management" action={<button className="rounded-xl bg-[#2563EB] px-7 py-5 font-extrabold text-white">+ Restock</button>} /><InventoryTable /></>;
  if (view === 'deliveries') return <><PageTitle title="Dispensed Log" subtitle="Today · 34 prescriptions dispensed" /><DataTable columns={['Time', 'Patient', 'Drug', 'Qty', 'Dispensed By']} rows={[['2:15 PM', 'Ngozi Udo', 'Amoxicillin 500mg', '14 caps', 'Pharmacist Mazi'], ['1:45 PM', 'Bola Adeleke', 'Ciprofloxacin 500mg', '14 tabs', 'Pharmacist Mazi'], ['12:30 PM', 'Chidinma Okafor', 'Paracetamol 500mg', '20 tabs', 'Pharmacist Mazi'], ['11:00 AM', 'Abiodun Eze', 'Metformin 500mg', '60 tabs', 'Pharmacist Mazi']]} /></>;
  if (view === 'settings') return <><PageTitle title="Settings" /><SettingsRows rows={[['Pharmacy Name', 'Central Pharmacy'], ['Facility', 'Ibom Specialist Hospital'], ['License No.', 'PCN-2026-01234'], ['Hours', '8:00 AM – 8:00 PM'], ['Emergency Line', '+234 803 111 2222']]} /></>;
  if (view === 'prescriptions') return <><PageTitle title="Prescriptions" subtitle="All prescription requests" action={<div className="flex gap-3"><button className="rounded-full bg-[#2563EB] px-6 py-3 font-bold text-white">Pending</button><button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3">Dispensed</button><button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3">All</button></div>} /><PrescriptionCards /></>;

  return (
    <>
      <PageTitle title="Pharmacy Overview" subtitle="Friday, 20 June 2026" />
      <StatGrid stats={[
        { title: 'Pending Prescriptions', value: '7', sub: '3 urgent', tone: 'amber' },
        { title: 'Dispensed Today', value: '34', sub: '+2 from yesterday', tone: 'slate' },
        { title: 'Low Stock Items', value: '3', sub: 'Reorder required', tone: 'rose' },
        { title: 'Expired Items', value: '0', sub: 'All stock in date', tone: 'sky' },
      ]} />
      <Card className="mt-9"><div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-black">Pending Prescriptions</h2><Link href="/pharmacy/prescriptions" className="rounded-xl border border-blue-200 px-6 py-3 font-bold text-[#2563EB]">View all</Link></div><PrescriptionCards compact /></Card>
    </>
  );
}

function AdminDashboard({ view }: { view: View }) {
  if (view === 'people') return <><PageTitle title="Users" subtitle="12,847 registered across all roles" /><DataTable columns={dashboardEntities.admin.table.columns} rows={dashboardEntities.admin.table.rows} /></>;
  if (view === 'facilities') return <><PageTitle title="Hospitals" subtitle="23 registered facilities" action={<Link href="/signup?type=hospital" className="rounded-xl bg-[#4f46e5] px-7 py-5 font-extrabold text-white">+ Register Hospital</Link>} /><div className="grid gap-6 md:grid-cols-2">{['Ibom Specialist Hospital|Uyo, AKS · Specialist|1,247|Active', 'Univ. of Uyo Teaching Hospital|Uyo, AKS · Teaching|2,104|Active', 'General Hospital Uyo|Uyo, AKS · General|892|Active', 'Meridian Clinic Eket|Eket, AKS · Private|—|Pending'].map((h) => { const [n, l, p, s] = h.split('|'); return <Card key={n}><div className="flex justify-between"><div><h3 className="text-xl font-black">{n}</h3><p className="mt-2 text-[#8a97b4]">{l}</p></div><Pill tone={s === 'Pending' ? 'urgent' : 'success'}>{s}</Pill></div><div className="mt-6 border-t border-slate-100 pt-5 flex justify-between text-lg"><span className="text-[#8a97b4]">Patients this month</span><b>{p}</b></div></Card>; })}</div></>;
  if (view === 'messages') return <><PageTitle title="Audit Log" subtitle="System event history" /><DataTable columns={['Time', 'Actor', 'Action', 'Target']} rows={[['14:22', 'system', 'HOSPITAL_REGISTERED', 'Meridian Clinic Eket'], ['14:04', 'admin@sv.ng', 'USER_SUSPENDED', 'john.doe@example.com'], ['13:45', 'ai-service', 'HIGH_LATENCY_ALERT', 'triage/analyze endpoint'], ['12:00', 'system', 'BACKUP_COMPLETED', 'db-prod-snapshot-20260620']]} /></>;
  if (view === 'vitals') return <><PageTitle title="System Health" subtitle="Real-time service status" /><div className="grid gap-6 md:grid-cols-2">{['API Server|99.97%|Operational', 'PostgreSQL Database|99.99%|Operational', 'WebSocket Service|99.92%|Operational', 'AI Triage Service|99.71%|Degraded — high latency'].map((s) => { const [name, up, status] = s.split('|'); return <Card key={name}><div className="flex items-center justify-between"><div className="flex items-center gap-5"><CheckCircle2 className={status.startsWith('Degraded') ? 'text-amber-500' : 'text-[#60A5FA]'} /><div><h3 className="text-xl font-black">{name}</h3><p className={status.startsWith('Degraded') ? 'text-amber-600' : 'text-[#2563EB]'}>{status}</p></div></div><div className="text-right"><b className="text-2xl">{up}</b><p className="text-[#8a97b4]">30-day uptime</p></div></div></Card>; })}</div></>;
  if (view === 'settings') return <><PageTitle title="Settings" /><SettingsRows rows={[['Platform Name', 'SynaptiVerse Health OS'], ['Version', 'v2.1.4'], ['Environment', 'Production'], ['Region', 'Nigeria — West Africa'], ['Support Email', 'admin@synaptiverse.ng']]} /></>;

  return (
    <>
      <PageTitle title="Platform Overview" subtitle="SynaptiVerse system dashboard · June 20, 2026" />
      <StatGrid stats={dashboardEntities.admin.stats} />
      <div className="mt-9 grid gap-6 xl:grid-cols-2">
        <Card className="min-h-[430px]"><h2 className="text-xl font-black">Platform Activity — Last 7 Days</h2><div className="mt-28 flex justify-around text-[#8a97b4]"><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span></div></Card>
        <Card><h2 className="mb-8 text-xl font-black">Recent System Events</h2>{dashboardEntities.admin.activity.map((item, i) => <div key={item} className="flex gap-4 border-b border-slate-100 py-4 last:border-0"><span className={`mt-2 h-2.5 w-2.5 rounded-full ${['bg-blue-500', 'bg-amber-500', 'bg-rose-500', 'bg-slate-400', 'bg-[#4f46e5]'][i]}`} /><div><p className="text-lg text-[#12284a]">{item}</p><p className="mt-1 text-sm text-[#8a97b4]">{['2 min ago', '18 min ago', '1 hour ago', '3 hours ago', '6 hours ago'][i]}</p></div></div>)}</Card>
      </div>
    </>
  );
}

function DepartmentCards({ full = false }: { full?: boolean }) {
  const deps = [
    ['Emergency', '8', '2/3 doctors', 'High Load', 85, 'bg-rose-500'],
    ['Cardiology', '3', '3/3 doctors', 'Normal', 40, 'bg-[#2563EB]'],
    ['General', '12', '4/5 doctors', 'Moderate', 68, 'bg-amber-500'],
    ['Pediatrics', '5', '2/3 doctors', 'Moderate', 45, 'bg-[#635bff]'],
    ['OB-GYN', '2', '2/2 doctors', 'Normal', 28, 'bg-[#60A5FA]'],
    ['Surgery', '1', '1/2 doctors', 'Normal', 18, 'bg-[#60A5FA]'],
  ];
  return <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">{deps.map(([name, waiting, doctors, load, fill, color]) => <Card key={name}><div className="flex justify-between"><h3 className="text-lg font-black">{name}</h3><span className="text-[#8a97b4]">{full ? load : doctors}</span></div><div className="mt-8 flex items-end justify-between gap-6"><b className="text-5xl font-black">{waiting}</b>{full ? <><b className="text-4xl">{String(doctors).split(' ')[0]}</b><b className="text-4xl">{Number(waiting) + 4}</b></> : null}</div><Progress value={Number(fill)} color={String(color)} /><p className="mt-3 text-[#8a97b4]">patients waiting</p></Card>)}</div>;
}

function AppointmentList({ hospital = false }: { hospital?: boolean }) {
  return <div className="space-y-5">{[['9:00 AM', 'Emeka Obi', 'Completed'], ['10:00 AM', 'Adaeze Chukwu', 'In Progress'], ['11:30 AM', 'James Akpan', 'Confirmed'], ['1:00 PM', 'Ngozi Udo', 'Confirmed']].map(([time, name, status]) => <Card key={time} className="flex items-center justify-between py-7"><div className="grid gap-1 md:grid-cols-[110px_1fr] md:items-center"><b className="text-lg text-[#6157f5]">{time}</b><div><h3 className="text-lg font-black">{name}</h3><p className="text-[#526783]">{hospital ? 'Dr. Okon Bassey · Cardiology' : name === 'Adaeze Chukwu' ? 'Urgent Triage' : 'New Patient'}</p></div></div><Pill tone={status === 'Completed' ? 'slate' : status === 'In Progress' ? 'routine' : 'violet'}>{status}</Pill></Card>)}</div>;
}

function ScheduleList() {
  return <div className="space-y-0">{['9:00 AM|Morning ward rounds', '10:00 AM|Emeka Obi · Consultation', '11:30 AM|Adaeze Chukwu · Triage', '1:00 PM|Lunch break', '2:30 PM|James Akpan · Follow-up', '4:00 PM|Ngozi Udo · New patient'].map((row) => { const [time, event] = row.split('|'); return <div key={row} className="grid grid-cols-[95px_1fr] border-b border-slate-100 py-4 last:border-0"><span className="text-[#8a97b4]">{time}</span><span className={event.includes('Adaeze') ? 'font-bold text-[#2563EB]' : ''}>{event}</span></div>; })}</div>;
}

function ScheduleGrid() {
  return <Card><div className="grid grid-cols-[80px_repeat(5,1fr)] gap-1 text-center text-sm"><span /><>{['Mon 20', 'Tue 21', 'Wed 22', 'Thu 23', 'Fri 24'].map((d) => <b key={d} className="border-b border-[#dbe3ef] py-3 text-[#526783]">{d}</b>)}</>{['9 AM', '10 AM', '11 AM', '12 PM', '1 PM', '2 PM', '3 PM', '4 PM'].map((t, i) => <><span key={`${t}-label`} className="py-5 text-right text-[#8a97b4]">{t}</span>{[0, 1, 2, 3, 4].map((d) => <div key={`${t}-${d}`} className={`min-h-14 rounded-lg border border-slate-100 bg-slate-50 p-4 font-bold ${i === 1 && d === 0 ? 'border-blue-200 bg-blue-50 text-[#2563EB]' : i === 2 && d === 0 ? 'border-amber-200 bg-amber-50 text-amber-500' : i === 0 && d === 1 ? 'border-violet-200 bg-violet-50 text-[#6157f5]' : i === 3 && d === 2 ? 'border-blue-200 bg-blue-50 text-[#2563EB]' : ''}`}>{i === 1 && d === 0 ? 'Emeka Obi' : i === 2 && d === 0 ? 'Adaeze C.' : i === 0 && d === 1 ? 'Ward rounds' : i === 3 && d === 2 ? 'James A.' : ''}</div>)}</>)}</div></Card>;
}

function Analytics({ title, subtitle, doctor = false }: { title: string; subtitle: string; doctor?: boolean }) {
  const labels = doctor ? [['Hypertension', 32, 'bg-[#2563EB]'], ['Chest Pain', 24, 'bg-[#6157f5]'], ['Arrhythmia', 18, 'bg-amber-500'], ['Heart Failure', 14, 'bg-rose-500'], ['Other', 12, 'bg-slate-300']] : [['Malaria', 23, 'bg-amber-500'], ['Hypertension', 18, 'bg-[#6157f5]'], ['UTI', 12, 'bg-[#2563EB]'], ['Typhoid', 10, 'bg-[#60A5FA]'], ['Other', 37, 'bg-slate-300']];
  return <><PageTitle title={title} subtitle={subtitle} /><StatGrid stats={[{ title: doctor ? 'Total Patients' : 'Total Encounters', value: doctor ? '84' : '1,247', sub: '', tone: 'slate' }, { title: doctor ? 'Avg. Consult' : 'Avg. Wait Time', value: doctor ? '22 min' : '38 min', sub: '', tone: 'slate' }, { title: 'Resolved', value: doctor ? '78' : '1,184', sub: '', tone: 'slate' }, { title: 'Rating', value: doctor ? '4.9 / 5' : '4.8 / 5', sub: '', tone: 'slate' }]} /><div className="mt-8 grid gap-6 xl:grid-cols-[1.05fr_1fr]"><Card className="min-h-[390px]"><h2 className="text-xl font-black">Patients Per Day</h2><div className="mt-32 flex justify-around text-[#8a97b4]"><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span></div></Card><Card><h2 className="mb-8 text-xl font-black">{doctor ? 'Conditions Breakdown' : 'Top Conditions'}</h2>{labels.map(([label, pct, color]) => <div key={String(label)} className="mb-5"><div className="mb-2 flex justify-between"><span className="text-[#526783]">{label}</span><b>{pct}%</b></div><Progress value={Number(pct) * 3} color={String(color)} /></div>)}</Card></div></>;
}

function Notifications() {
  return <><PageTitle title="Notifications" subtitle="Recent alerts and updates" /><div className="space-y-4">{[['Critical escalation: Bola Adeleke', 'BP 185/115 in Emergency. Immediate attention required.', 'bg-rose-50 border-rose-200 border-l-4 border-l-rose-500'], ['Queue capacity warning', 'Emergency department at 85% capacity — 8 patients waiting.', 'bg-amber-50 border-amber-200 border-l-4 border-l-amber-500'], ['New specialist registered', 'Dr. Amadi Chukwu, Neurologist, has joined the network.', 'bg-indigo-50 border-indigo-200 border-l-4 border-l-[#6157f5]'], ['Monthly analytics report ready', 'June 2026 patient encounter report is available for download.', 'bg-white border-[#dbe3ef] border-l-4 border-l-slate-400']].map(([h, b, c]) => <section key={h} className={`rounded-[18px] border p-7 ${c}`}><h3 className="text-lg font-black">{h}</h3><p className="mt-3 text-[#334b68]">{b}</p><p className="mt-4 text-[#8a97b4]">5 min ago</p></section>)}</div></>;
}

function SettingsRows({ rows, hero, sub, initials }: { rows: string[][]; hero?: string; sub?: string; initials?: string }) {
  return <div className="max-w-[700px] space-y-4">{hero ? <Card className="flex items-center justify-between"><div className="flex items-center gap-5"><div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#2563EB] text-2xl font-black text-white">{initials}</div><div><h2 className="text-xl font-black">{hero}</h2><p className="text-[#526783]">{sub}</p></div></div><button className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">Edit</button></Card> : null}{rows.map(([label, value]) => <div key={label} className="flex items-center justify-between rounded-[14px] border border-[#dbe3ef] bg-white px-7 py-5"><span className="text-[#8a97b4]">{label}</span><b>{value}</b></div>)}</div>;
}

function PrescriptionCards({ compact = false }: { compact?: boolean }) {
  const items = [['Adaeze Chukwu', 'Aspirin 75mg + Atorvastatin 40mg', 'URGENT'], ['Emeka Obi', 'Amlodipine 5mg + Lisinopril 10mg', 'URGENT'], ['James Akpan', 'Metoprolol 50mg (30-day supply)', 'ROUTINE']];
  return <div className="space-y-5">{items.map(([name, drug, urgency]) => <article key={name} className={`${compact ? 'bg-slate-50' : 'bg-white border border-[#dbe3ef]'} flex items-center justify-between rounded-[18px] p-6`}><div><h3 className="text-xl font-black">{name} <Pill tone={urgency === 'URGENT' ? 'urgent' : 'routine'}>{urgency}</Pill></h3><p className="mt-3 text-lg text-[#334b68]">{drug}</p><p className="mt-2 text-[#8a97b4]">Prescribed by Dr. Okon Bassey · 35 min ago</p></div><button className="rounded-xl bg-[#2563EB] px-7 py-3 font-bold text-white">Dispense</button></article>)}</div>;
}

function InventoryTable() {
  return <DataTable columns={['Drug Name', 'Category', 'Stock', 'Unit', 'Reorder At', 'Status']} rows={[['Aspirin 75mg', 'Cardiovascular', 450, 'Tablets', 100, 'Good'], ['Amlodipine 5mg', 'Antihypertensive', 85, 'Tablets', 100, 'Low'], ['Amoxicillin 500mg', 'Antibiotic', 320, 'Capsules', 150, 'Good'], ['Ciprofloxacin 500mg', 'Antibiotic', 40, 'Tablets', 80, 'Critical'], ['Metformin 500mg', 'Antidiabetic', 600, 'Tablets', 200, 'Good'], ['Paracetamol 500mg', 'Analgesic', 55, 'Tablets', 200, 'Low']]} />;
}

function LabDashboard({ view }: { view: View }) {
  if (view === 'requests') {
    return (
      <>
        <PageTitle title="Test Requests" subtitle="All laboratory test orders" />
        <div className="mb-8 flex flex-wrap gap-3">
          <button className="rounded-full bg-[#2563EB] px-6 py-3 font-bold text-white">Pending</button>
          <button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3 text-[#526783]">In Progress</button>
          <button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3 text-[#526783]">Completed</button>
        </div>
        <div className="space-y-5">
          {[
            ['Adaeze Chukwu', 'Cardiac Enzyme Panel (Troponin)', 'Ordered by Dr. Okon Bassey · 45 min ago', 'URGENT'],
            ['Bola Adeleke', 'Malaria RDT + Blood Culture', 'Ordered by Dr. Bello Eze · 20 min ago', 'CRITICAL'],
          ].map(([name, test, meta, urgency]) => (
            <Card key={name} className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black">{name} <Pill tone={urgency === 'CRITICAL' ? 'critical' : 'urgent'}>{urgency}</Pill></h3>
                <p className="mt-4 text-lg font-bold text-[#12284a]">{test}</p>
                <p className="mt-2 text-[#8a97b4]">{meta}</p>
              </div>
              <button className="rounded-xl bg-[#2563EB] px-7 py-3 font-extrabold text-white">Start Test</button>
            </Card>
          ))}
        </div>
      </>
    );
  }

  if (view === 'results') {
    return (
      <>
        <PageTitle title="Test Results" subtitle="28 results today" />
        <RoleTable
          columns={['Patient', 'Test', 'Result Summary', 'Status', 'Date']}
          rows={[
            ['James Akpan', 'Lipid Profile', 'LDL 4.2 — Elevated', <Pill key="abn" tone="urgent">Abnormal</Pill>, 'Today 1:30 PM'],
            ['Ngozi Udo', 'Urinalysis', 'E. coli — UTI confirmed', <Pill key="abn2" tone="urgent">Abnormal</Pill>, 'Today 12:00 PM'],
            ['Chidinma Okafor', 'Full Blood Count', 'All within normal range', <Pill key="ok" tone="success">Normal</Pill>, 'Today 10:30 AM'],
            ['Abiodun Eze', 'HbA1c', '7.8% — Above target', <Pill key="abn3" tone="urgent">Abnormal</Pill>, 'Today 9:00 AM'],
            ['Bola Adeleke', 'Malaria RDT', 'P. falciparum — Positive', <Pill key="crit" tone="critical">Critical</Pill>, 'Today 2:00 PM'],
          ]}
        />
      </>
    );
  }

  if (view === 'equipment' || view === 'collections') {
    const equipment = [
      ['Haematology Analyser', 'Online', '18', 'Jun 15, 2026', true],
      ['Chemistry Analyser', 'Online', '24', 'Jun 18, 2026', true],
      ['Centrifuge Bank (x2)', 'Online', '42', 'Jun 10, 2026', true],
      ['Urinalysis Analyser', 'Online', '12', 'Jun 20, 2026', true],
      ['Microscope Station', 'Online', '8', 'Jun 12, 2026', true],
      ['PCR Thermocycler', 'Maintenance', '0', 'Jun 5, 2026', false],
    ] as const;
    return (
      <>
        <PageTitle title="Equipment" subtitle="7 laboratory instruments" />
        <div className="grid gap-6 xl:grid-cols-2">
          {equipment.map(([name, status, tests, calibrated, online]) => (
            <Card key={name}>
              <div className="flex items-center gap-5">
                <CheckCircle2 className={`h-8 w-8 ${online ? 'text-[#60A5FA]' : 'text-[#f59e0b]'}`} />
                <div>
                  <h3 className="text-xl font-black">{name}</h3>
                  <div className="mt-4 flex flex-wrap gap-8 text-[#526783]">
                    <Pill tone={online ? 'success' : 'urgent'}>{status}</Pill>
                    <span>Tests today: <b className="text-[#020b22]">{tests}</b></span>
                    <span>Calibrated: <b className="text-[#020b22]">{calibrated}</b></span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </>
    );
  }

  if (view === 'settings') {
    return (
      <>
        <PageTitle title="Settings" />
        <SettingsRows rows={[['Lab Name', 'Diagnostic Laboratory'], ['Facility', 'Ibom Specialist Hospital'], ['Lab Director', 'Dr. Chidi Obi'], ['Accreditation', 'NAFDAC-LAB-2026-0145'], ['Hours', '7:00 AM – 9:00 PM']]} />
      </>
    );
  }

  return (
    <>
      <PageTitle title="Laboratory Overview" subtitle="Friday, 20 June 2026" />
      <StatGrid stats={[
        { title: 'Pending Tests', value: '12', sub: '3 urgent, 1 critical', tone: 'amber' },
        { title: 'Completed Today', value: '28', sub: '+15 from yesterday', tone: 'slate' },
        { title: 'Critical Results', value: '2', sub: 'Require immediate action', tone: 'rose' },
        { title: 'Equipment Online', value: '6/7', sub: '1 in maintenance', tone: 'slate' },
      ]} />
      <div className="mt-9 grid gap-6 xl:grid-cols-[1.05fr_1fr]">
        <Card>
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-black">Urgent Test Requests</h2>
            <Link href="/lab/requests" className="rounded-xl border border-blue-200 px-6 py-3 font-bold text-[#2563EB]">View all</Link>
          </div>
          <div className="space-y-5">
            {[
              ['Adaeze Chukwu', 'Cardiac Enzyme Panel (Troponin)', 'Ordered by Dr. Okon Bassey · 45 min ago', 'URGENT', 'Start Test'],
              ['Bola Adeleke', 'Malaria RDT + Blood Culture', 'Ordered by Dr. Bello Eze · 20 min ago', 'CRITICAL', 'Start Test'],
              ['Emeka Obi', 'Full Blood Count + Electrolytes', 'Ordered by Dr. Okon Bassey · 1 hour ago', 'URGENT', 'In Progress'],
            ].map(([name, test, meta, urgency, action]) => (
              <article key={name} className="rounded-[16px] border border-blue-200 bg-blue-50 p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-black">{name} <Pill tone={urgency === 'CRITICAL' ? 'critical' : 'urgent'}>{urgency}</Pill></h3>
                    <p className="mt-4 text-lg text-[#334b68]">{test}</p>
                    <p className="mt-2 text-[#8a97b4]">{meta}</p>
                  </div>
                  <button className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">{action}</button>
                </div>
              </article>
            ))}
          </div>
        </Card>
        <Card>
          <h2 className="mb-6 text-xl font-black">Recent Results</h2>
          {[
            ['James Akpan', 'Lipid Profile', 'LDL: 4.2 mmol/L — Elevated', 'Abnormal'],
            ['Ngozi Udo', 'Urinalysis + Culture', 'E. coli detected — UTI confirmed', 'Abnormal'],
            ['Chidinma Okafor', 'Full Blood Count', 'All values within normal range', 'Normal'],
            ['Bola Adeleke', 'Malaria RDT', 'P. falciparum — Positive', 'Critical'],
          ].map(([name, test, result, status]) => (
            <div key={name} className="border-b border-slate-100 py-5 last:border-0">
              <div className="flex justify-between gap-4">
                <h3 className="font-black">{name}</h3>
                <Pill tone={status === 'Critical' ? 'critical' : status === 'Normal' ? 'success' : 'urgent'}>{status}</Pill>
              </div>
              <p className="mt-2 text-[#8a97b4]">{test}</p>
              <p className="mt-1 text-[#334b68]">{result}</p>
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}

function HmoDashboard({ view }: { view: View }) {
  if (view === 'claims') {
    return (
      <>
        <PageTitle title="Claims" subtitle="347 claims this month" />
        <div className="mb-8 flex flex-wrap gap-3">
          {['All', 'Pending', 'Approved', 'Denied'].map((tab) => <button key={tab} className={`rounded-full px-6 py-3 ${tab === 'Pending' ? 'bg-[#2563EB] font-bold text-white' : 'border border-[#dbe3ef] bg-white text-[#526783]'}`}>{tab}</button>)}
        </div>
        <RoleTable
          columns={['Claim ID', 'Member', 'Hospital', 'Amount', 'Date', 'Status', 'Actions']}
          rows={[
            ['CLM-001234', 'Adaeze Chukwu', 'Ibom Specialist Hospital', <b key="amt">₦45,000</b>, 'Jun 20', <Pill key="p" tone="urgent">Pending</Pill>, <div key="a" className="flex gap-2"><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold text-[#2563EB]">Approve</button><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold text-rose-500">Deny</button></div>],
            ['CLM-001229', 'Emeka Obi', 'Ibom Specialist Hospital', <b key="amt2">₦120,000</b>, 'Jun 20', <Pill key="p2" tone="urgent">Pending</Pill>, <div key="a2" className="flex gap-2"><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold text-[#2563EB]">Approve</button><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold text-rose-500">Deny</button></div>],
          ]}
        />
      </>
    );
  }

  if (view === 'members' || view === 'patients') {
    return (
      <>
        <PageTitle title="Members" subtitle="4,821 active members" />
        <RoleTable
          columns={['Member', 'Plan', 'Enrolled', 'Claims', 'Status']}
          rows={[
            ['Adaeze Chukwu', <Pill key="gold" tone="urgent">Gold</Pill>, 'Jan 2025', <b key="3">3</b>, <Pill key="a" tone="success">Active</Pill>],
            ['Emeka Obi', <Pill key="plat" tone="violet">Platinum</Pill>, 'Mar 2024', <b key="7">7</b>, <Pill key="a2" tone="success">Active</Pill>],
            ['James Akpan', <Pill key="silver" tone="slate">Silver</Pill>, 'Jun 2025', <b key="2">2</b>, <Pill key="a3" tone="success">Active</Pill>],
            ['Ngozi Udo', <Pill key="silver2" tone="slate">Silver</Pill>, 'Aug 2025', <b key="1">1</b>, <Pill key="a4" tone="success">Active</Pill>],
            ['Bola Adeleke', <Pill key="gold2" tone="urgent">Gold</Pill>, 'Nov 2024', <b key="4">4</b>, <Pill key="i" tone="slate">Inactive</Pill>],
          ]}
        />
      </>
    );
  }

  if (view === 'analytics' || view === 'utilization') {
    return (
      <>
        <PageTitle title="Analytics" subtitle="Claims and spend insights · June 2026" />
        <div className="grid gap-6 xl:grid-cols-2">
          <Card><h2 className="text-xl font-black">Monthly Claims Volume</h2><MockChart labels={['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']} /></Card>
          <Card><h2 className="mb-8 text-xl font-black">Top Conditions Covered</h2><MetricBars items={[['Hypertension', 28, 'bg-[#2563EB]'], ['Malaria', 22, 'bg-[#6157f5]'], ['Diabetes', 18, 'bg-[#60A5FA]'], ['UTI', 15, 'bg-[#2563EB]'], ['Other', 17, 'bg-slate-300']]} /></Card>
        </div>
        <Card className="mt-6">
          <h2 className="mb-8 text-xl font-black">Claims by Hospital</h2>
          {[
            ['Ibom Specialist Hospital', '₦4.2M', 98],
            ['General Hospital Uyo', '₦2.1M', 62],
            ['University Teaching Hospital', '₦1.8M', 39],
            ['Other facilities', '₦0.3M', 19],
          ].map(([name, amount, width]) => (
            <div key={name} className="mb-5 grid items-center gap-4 md:grid-cols-[320px_1fr_90px]">
              <span className="text-[#334b68]">{name}</span>
              <Progress value={Number(width)} color="bg-[#2563EB]" />
              <b>{amount}</b>
            </div>
          ))}
        </Card>
      </>
    );
  }

  if (view === 'settings') {
    return (
      <>
        <PageTitle title="Settings" />
        <SettingsRows rows={[['HMO Name', 'HealthBridge HMO'], ['License', 'NHIS-2026-HMO-00451'], ['Coverage Region', 'Akwa Ibom, Cross River, Rivers'], ['Partner Facilities', '23 active'], ['Claims Email', 'claims@healthbridge.ng']]} />
      </>
    );
  }

  return (
    <>
      <PageTitle title="Insurance Overview" subtitle="HealthBridge HMO · June 2026" />
      <StatGrid stats={[
        { title: 'Active Members', value: '4,821', sub: '+48 this month', tone: 'slate' },
        { title: 'Claims This Month', value: '347', sub: 'Up from 298 last month', tone: 'slate' },
        { title: 'Approved Claims', value: '289', sub: '₦8.4M total payout', tone: 'sky' },
        { title: 'Pending Review', value: '58', sub: '12 flagged for audit', tone: 'amber' },
      ]} />
      <Card className="mt-9">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-black">Claims Requiring Action</h2>
          <Link href="/hmo/claims" className="rounded-xl border border-blue-200 px-6 py-3 font-bold text-[#2563EB]">View all</Link>
        </div>
        {[
          ['Adaeze Chukwu', 'CLM-001234', 'Ibom Specialist Hospital · Jun 20', '₦45,000'],
          ['Emeka Obi', 'CLM-001229', 'Ibom Specialist Hospital · Jun 20', '₦120,000'],
        ].map(([name, id, meta, amount]) => (
          <article key={id} className="mb-4 flex items-center justify-between gap-4 rounded-[16px] border border-blue-200 bg-blue-50 p-6">
            <div><h3 className="text-lg font-black">{name} <span className="ml-2 font-mono text-xs text-[#8a97b4]">{id}</span></h3><p className="mt-3 text-[#526783]">{meta}</p></div>
            <div className="flex items-center gap-3"><b className="text-xl">{amount}</b><button className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Approve</button><button className="rounded-xl border border-rose-200 bg-white px-6 py-3 font-bold text-rose-500">Deny</button></div>
          </article>
        ))}
      </Card>
    </>
  );
}

function MohDashboard({ view }: { view: View }) {
  if (view === 'reports') {
    return (
      <>
        <PageTitle title="State Reports" subtitle="Patient encounter data by LGA" action={<div className="flex gap-3"><button className="rounded-xl border border-[#dbe3ef] bg-white px-7 py-5 font-bold">June 2026⌄</button><button className="rounded-xl bg-[#2563EB] px-7 py-5 font-bold text-white">Export CSV</button></div>} />
        <StatGrid stats={[
          { title: 'Total Encounters', value: '42,819', sub: '', tone: 'slate' },
          { title: 'Unique Patients', value: '31,204', sub: '', tone: 'slate' },
          { title: 'AI Triage', value: '18,234', sub: '', tone: 'slate' },
          { title: 'Facilities Reporting', value: '156', sub: '', tone: 'slate' },
        ]} />
        <div className="mt-8">
          <RoleTable columns={['LGA', 'Facilities', 'Patient Volume', 'Top Condition', 'AI Triage %']} rows={[
            ['Uyo', '34', <b key="1">12,450</b>, 'Hypertension', <b key="p1" className="text-[#2563EB]">74%</b>],
            ['Eket', '18', <b key="2">6,820</b>, 'Malaria', <b key="p2" className="text-[#2563EB]">68%</b>],
            ['Ikot Ekpene', '22', <b key="3">7,340</b>, 'Malaria', <b key="p3" className="text-[#2563EB]">71%</b>],
            ['Oron', '12', <b key="4">4,210</b>, 'UTI', <b key="p4" className="text-[#2563EB]">65%</b>],
            ['Abak', '14', <b key="5">4,890</b>, 'Typhoid', <b key="p5" className="text-[#2563EB]">70%</b>],
            ['Etinan', '10', <b key="6">3,560</b>, 'Hypertension', <b key="p6" className="text-[#2563EB]">72%</b>],
          ]} />
        </div>
      </>
    );
  }

  if (view === 'facilities') {
    return (
      <>
        <PageTitle title="Registered Hospitals" subtitle="156 facilities across Akwa Ibom" action={<button className="rounded-xl border border-[#dbe3ef] bg-white px-7 py-5 font-bold">All LGAs⌄</button>} />
        <RoleTable columns={['Facility', 'LGA', 'Type', 'Status', 'Patients', 'SynaptiVerse']} rows={[
          ['Ibom Specialist Hospital', 'Uyo', 'Specialist', <Pill key="a" tone="success">Active</Pill>, <b key="p">5,420</b>, <Pill key="e" tone="success">Enrolled</Pill>],
          ['Univ. of Uyo Teaching Hospital', 'Uyo', 'Teaching', <Pill key="a2" tone="success">Active</Pill>, <b key="p2">8,103</b>, <Pill key="e2" tone="success">Enrolled</Pill>],
          ['General Hospital Uyo', 'Uyo', 'General', <Pill key="a3" tone="success">Active</Pill>, <b key="p3">3,204</b>, <Pill key="e3" tone="success">Enrolled</Pill>],
          ['Eket General Hospital', 'Eket', 'General', <Pill key="a4" tone="success">Active</Pill>, <b key="p4">2,810</b>, <Pill key="e4" tone="slate">Not enrolled</Pill>],
          ['Ikot Ekpene Gen. Hospital', 'Ikot Ekpene', 'General', <Pill key="a5" tone="success">Active</Pill>, <b key="p5">2,540</b>, <Pill key="e5" tone="success">Enrolled</Pill>],
          ['Oron General Hospital', 'Oron', 'General', <Pill key="a6" tone="slate">Inactive</Pill>, '—', <Pill key="e6" tone="slate">Not enrolled</Pill>],
        ]} />
      </>
    );
  }

  if (view === 'surveillance') {
    return (
      <>
        <PageTitle title="Disease Surveillance" subtitle="Real-time epidemiological monitoring · Akwa Ibom" />
        <div className="space-y-6">
          {[
            ['Malaria', 'Alert', '+23% in 14 days', 'Hotspot: Uyo, Eket, Ikot Ekpene', 'bg-[#f59e0b]', [48, 55, 43, 59, 66, 76, 88]],
            ['Hypertension', 'Normal', 'Stable — within baseline', 'Hotspot: Uyo, Abak', 'bg-[#2563EB]', [60, 63, 55, 61, 66, 62, 59]],
            ['Typhoid Fever', 'Improving', '−12% improvement', 'Hotspot: Ini, Ikot Ekpene', 'bg-[#60A5FA]', [48, 45, 40, 35, 33, 30, 25]],
            ['UTI Cluster', 'Alert', 'Cluster detected in Eket', 'Hotspot: Eket LGA', 'bg-rose-500', [8, 10, 12, 16, 20, 26, 33]],
          ].map(([name, status, trend, hotspot, color, values]) => (
            <Card key={String(name)} className="flex items-center justify-between gap-6">
              <div>
                <h3 className="text-2xl font-black">{name} <Pill tone={status === 'Alert' ? 'urgent' : status === 'Improving' ? 'success' : 'routine'}>{status}</Pill> <span className="ml-3 text-base font-normal text-[#526783]">{trend}</span></h3>
                <p className="mt-4 text-[#8a97b4]">{hotspot}</p>
              </div>
              <SparkBars color={String(color)} values={values as number[]} />
            </Card>
          ))}
        </div>
      </>
    );
  }

  if (view === 'settings') {
    return (
      <>
        <PageTitle title="Settings" />
        <SettingsRows rows={[['Agency', 'Akwa Ibom State Ministry of Health'], ['Commissioner', 'Hon. Dr. Emen Offiong'], ['Headquarters', 'Uyo, Akwa Ibom State'], ['State Code', 'AKS-MOH-NG'], ['SynaptiVerse Tier', 'State Government Partner']]} />
      </>
    );
  }

  return (
    <>
      <PageTitle title="State Health Overview" subtitle="Akwa Ibom State · June 2026" />
      <StatGrid stats={dashboardEntities.moh.stats} />
      <Card className="mt-9">
        <h2 className="mb-6 text-xl font-black">Akwa Ibom State — Facility Map</h2>
        <GoogleMapEmbed title="Akwa Ibom State facility map" query="hospitals in Akwa Ibom State Nigeria" />
      </Card>
      <Card className="mt-6">
        <h2 className="mb-6 text-xl font-black">Active Health Alerts</h2>
        <div className="space-y-4">
          <section className="rounded-[14px] border border-amber-300 bg-amber-50 p-6"><h3 className="font-black">Malaria Uptick — Uyo LGA</h3><p className="mt-3 text-[#334b68]">23% increase in cases over the past 14 days. Highest concentration in Itam and Nsit Ibom. Intervention recommended.</p></section>
          <section className="rounded-[14px] border border-rose-200 bg-rose-50 p-6"><h3 className="font-black">UTI Cluster — Eket LGA</h3><p className="mt-3 text-[#334b68]">12 cluster cases across 3 facilities. Likely linked to water quality in Eket Central ward. Investigation ongoing.</p></section>
        </div>
      </Card>
    </>
  );
}

function ClinicDashboard({ view }: { view: View }) {
  if (view === 'people') {
    const doctors = [
      ['UE', 'Dr. Uche Effiong', 'General Practice', 'ON DUTY', '9', 'Samuel Udofia · 10:30 AM'],
      ['EO', 'Dr. Emeka Okon', 'Internal Medicine', 'ON DUTY', '5', 'Ngozi Eze · 11:00 AM'],
      ['AE', 'Dr. Amaka Eze', 'Paediatrics', 'OFF', '0', 'Off duty'],
    ];
    return (
      <>
        <PageTitle title="Clinic Doctors" action={<Link href="/signup?type=specialist" className="rounded-xl bg-[#2563EB] px-7 py-5 font-bold text-white">+ Invite Doctor</Link>} />
        <div className="grid gap-6 xl:grid-cols-2">
          {doctors.map(([initials, name, specialty, status, patients, next]) => (
            <Card key={name}>
              <div className="flex justify-between gap-5">
                <div className="flex gap-4">
                  <div className="grid h-12 w-12 place-items-center rounded-xl bg-[#2563EB] text-lg font-black text-white">{initials}</div>
                  <div><h3 className="text-xl font-black">{name}</h3><p className="text-[#526783]">{specialty}</p></div>
                </div>
                <Pill tone={status === 'OFF' ? 'slate' : 'success'}>{status}</Pill>
              </div>
              <div className="mt-5 grid grid-cols-2 rounded-xl bg-slate-50 p-4">
                <div><p className="text-sm text-[#8a97b4]">Patients today</p><b className="text-2xl">{patients}</b></div>
                <div><p className="text-sm text-[#8a97b4]">Up next</p><p>{next}</p></div>
              </div>
              <div className="mt-5 flex gap-3"><Link href="/clinic/appointments" className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">View schedule</Link><button className={`rounded-xl border px-6 py-3 font-bold ${status === 'OFF' ? 'border-blue-200 text-[#2563EB]' : 'border-rose-200 text-rose-500'}`}>{status === 'OFF' ? 'Mark on' : 'Mark off'}</button></div>
            </Card>
          ))}
        </div>
      </>
    );
  }

  if (view === 'queue') {
    const waiting = [['Blessing Etim', 'SV-00821 · Wait: 5 min', 'URGENT'], ['Samuel Udofia', 'SV-00819 · Wait: 22 min', 'MODERATE']];
    return (
      <>
        <PageTitle title="Patient Queue" subtitle="7 patients — 2 urgent" action={<div className="flex gap-3">{['All', 'Urgent', 'Moderate', 'Low'].map((tab) => <button key={tab} className={`rounded-full px-5 py-2 ${tab === 'All' ? 'bg-[#2563EB] font-bold text-white' : 'border border-[#dbe3ef] bg-white text-[#526783]'}`}>{tab}</button>)}</div>} />
        <div className="grid gap-6 xl:grid-cols-3">
          <section><h2 className="mb-4 font-extrabold uppercase tracking-[0.12em] text-[#526783]">Waiting <Pill tone="slate">4</Pill></h2><div className="space-y-4">{waiting.map(([name, meta, urgency]) => <Card key={name} className="p-5"><div className="flex justify-between"><h3 className="font-black">{name}</h3><Pill tone={urgency === 'URGENT' ? 'urgent' : 'routine'}>{urgency}</Pill></div><p className="mt-3 text-[#8a97b4]">{meta}</p><div className="mt-4 flex gap-3"><button className="rounded-xl bg-[#2563EB] px-4 py-2 font-bold text-white">See now</button><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Vitals</button></div></Card>)}</div></section>
          <section><h2 className="mb-4 font-extrabold uppercase tracking-[0.12em] text-[#526783]">Being Seen <Pill tone="slate">2</Pill></h2><Card className="p-5"><div className="flex justify-between"><h3 className="font-black">Grace Nwachukwu</h3><Pill tone="slate">LOW</Pill></div><p className="mt-3 text-[#8a97b4]">SV-00817 · Wait: 38 min</p><div className="mt-4 flex gap-3"><button className="rounded-xl border border-blue-200 px-4 py-2 font-bold text-[#2563EB]">Resolve</button><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Vitals</button></div></Card></section>
          <section><h2 className="mb-4 font-extrabold uppercase tracking-[0.12em] text-[#526783]">Resolved <Pill tone="slate">1</Pill></h2><Card className="p-5"><h3 className="font-black">Peter Akpan</h3><p className="mt-3 text-[#8a97b4]">SV-00814 · Wait: 55 min</p><button className="mt-4 rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Vitals</button></Card><div className="mt-4 rounded-[18px] border border-dashed border-[#dbe3ef] p-5"><h3 className="font-black">Peter Akpan</h3><p className="mt-2 text-sm text-[#8a97b4]">SV-00814 · Resolved 10:42 AM</p><Pill tone="success">DONE</Pill></div></section>
        </div>
      </>
    );
  }

  if (view === 'appointments') {
    return (
      <>
        <PageTitle title="Appointments" action={<div className="flex gap-3"><button className="rounded-full bg-[#2563EB] px-6 py-3 font-bold text-white">Today</button><button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3">Week</button><button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3">Month</button><button className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">+ New slot</button></div>} />
        <RoleTable columns={['Time', 'Patient', 'Type', 'Doctor', 'Status', '']} rows={[
          [<b key="t" className="text-[#2563EB]">9:00 AM</b>, 'Chinwe Obi', 'Follow-up', 'Dr. Effiong', <Pill key="d" tone="success">DONE</Pill>, ''],
          [<b key="t2" className="text-[#2563EB]">10:30 AM</b>, 'Musa Ibrahim', 'New patient', 'Dr. Effiong', <Pill key="d2" tone="success">DONE</Pill>, ''],
          [<b key="t3" className="text-[#2563EB]">11:00 AM</b>, 'Ngozi Eze', 'Lab review', 'Dr. Okon', <Pill key="u" tone="urgent">UPCOMING</Pill>, <Link key="r" href="/clinic/appointments" className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Reschedule</Link>],
          [<b key="t4" className="text-[#2563EB]">2:00 PM</b>, 'Emeka James', 'Routine check', 'Dr. Effiong', <Pill key="u2" tone="urgent">UPCOMING</Pill>, <Link key="r2" href="/clinic/appointments" className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Reschedule</Link>],
          [<b key="t5" className="text-[#2563EB]">3:30 PM</b>, 'Amaka Uche', 'Prescription', 'Dr. Okon', <Pill key="u3" tone="urgent">UPCOMING</Pill>, <Link key="r3" href="/clinic/appointments" className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Reschedule</Link>],
        ]} />
      </>
    );
  }

  if (view === 'analytics') {
    return (
      <>
        <PageTitle title="Analytics" />
        <div className="grid gap-6 xl:grid-cols-2">
          <Card><h2 className="text-xl font-black">Daily Patient Volume — Last 7 Days</h2><MockChart /></Card>
          <Card><h2 className="mb-8 text-xl font-black">Condition Breakdown</h2><MetricBars items={[['Malaria / Fever', 34, 'bg-[#2563EB]'], ['Hypertension', 22, 'bg-[#6157f5]'], ['Respiratory', 15, 'bg-[#2563EB]'], ['Injuries', 12, 'bg-[#f59e0b]'], ['Other', 17, 'bg-slate-400']]} /></Card>
        </div>
        <div className="mt-6 grid gap-6 md:grid-cols-3"><StatCard title="Avg. Wait Time" value="28 min" sub="↓ 6 min" tone="sky" /><StatCard title="Fulfillment Rate" value="94%" sub="↑ 2%" tone="sky" /><StatCard title="No-show Rate" value="8%" sub="↑ 1%" tone="rose" /></div>
      </>
    );
  }

  if (view === 'notifications') return <ClinicNotifications />;

  if (view === 'settings') {
    return (
      <>
        <PageTitle title="Clinic Settings" />
        <div className="grid gap-6 xl:grid-cols-2">
          <Card><h2 className="mb-6 text-xl font-black">Clinic Profile</h2><div className="space-y-5"><TextField label="Clinic name" value="Meridian Clinic Eket" /><TextField label="Registration number" value="RC-20180023" /><TextField label="Address" value="45 Atu Road, Eket, Akwa Ibom" /></div><button className="mt-5 rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Save</button></Card>
          <Card><h2 className="mb-6 text-xl font-black">Operating Hours</h2><div className="space-y-5"><TextField label="Monday – Friday" value="8:00 AM – 6:00 PM" /><TextField label="Saturday" value="9:00 AM – 2:00 PM" /><TextField label="Sunday" value="Closed" /></div><button className="mt-5 rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Save</button></Card>
        </div>
      </>
    );
  }

  return (
    <>
      <PageTitle title="Good morning, Clinic Admin" subtitle="Friday, 20 June 2026 · Meridian Clinic Eket" />
      <StatGrid stats={[
        { title: 'In Queue', value: '7', sub: '2 urgent', tone: 'amber' },
        { title: 'Seen Today', value: '14', sub: '+3 from yesterday', tone: 'sky' },
        { title: 'Appointments', value: '5', sub: 'remaining today', tone: 'slate' },
        { title: 'Avg Wait Time', value: '28 min', sub: '↓ 6 min', tone: 'sky' },
      ]} />
      <div className="mt-8 grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <Card><div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-black">Live Queue</h2><Link href="/clinic/queue" className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">Full view →</Link></div>{['Blessing Etim|SV-00821 · 5 min wait|URGENT', 'Samuel Udofia|SV-00819 · 22 min wait|MODERATE', 'Grace Nwachukwu|SV-00817 · 38 min wait|LOW'].map((row, i) => { const [name, meta, tone] = row.split('|'); return <div key={name} className="flex items-center justify-between border-b border-slate-100 py-4 last:border-0"><div className="flex items-center gap-4"><span className="grid h-8 w-8 place-items-center rounded-full bg-slate-100 font-bold text-[#526783]">{i + 1}</span><div><h3 className="font-black">{name}</h3><p className="text-[#8a97b4]">{meta}</p></div></div><Pill tone={tone === 'URGENT' ? 'urgent' : tone === 'LOW' ? 'slate' : 'routine'}>{tone}</Pill></div>; })}</Card>
        <Card><h2 className="mb-6 text-xl font-black">Today's Appointments</h2><ScheduleList /><Link href="/clinic/appointments" className="mt-6 block w-full rounded-xl border border-[#dbe3ef] px-6 py-3 text-center font-bold">View all →</Link></Card>
      </div>
      <Card className="mt-6"><h2 className="mb-6 text-xl font-black">Quick Vitals Entry</h2><div className="grid gap-4 md:grid-cols-5">{['Blood Pressure|120/80 mmHg', 'Temperature|36.6 °C', 'SpO2|98 %', 'Pulse|72 bpm', 'Weight|68 kg'].map((item) => { const [label, value] = item.split('|'); return <div key={label} className="rounded-xl bg-slate-50 p-4"><p className="text-sm text-[#8a97b4]">{label}</p><b className="text-2xl">{value}</b></div>; })}</div><button className="mt-5 rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Save Vitals</button></Card>
    </>
  );
}

function ClinicNotifications() {
  return (
    <>
      <PageTitle title="Notifications" />
      <Card>
        {[
          ['URGENT: Blessing Etim — Chest pain, awaiting triage', '2 min ago', 'bg-rose-500'],
          ['Dr. Amaka Eze went off duty at 12:00 PM', '1 hour ago', 'bg-amber-500'],
          ['Appointment cancelled: Yusuf Bello — 3:00 PM slot now open', '2 hours ago', 'bg-[#6157f5]'],
          ['Queue resolved: 6 patients seen today so far', '3 hours ago', 'bg-[#2563EB]'],
          ['Prescription fulfilled: Chinwe Obi — Chloroquine, Amoxicillin', '4 hours ago', 'bg-[#2563EB]'],
        ].map(([text, time, dot]) => (
          <div key={text} className="flex items-center justify-between border-b border-slate-100 py-5 last:border-0">
            <div><h3 className="font-bold text-[#12284a]">{text}</h3><p className="mt-1 text-[#8a97b4]">{time}</p></div>
            <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
          </div>
        ))}
      </Card>
    </>
  );
}

function NurseDashboard({ view }: { view: View }) {
  if (view === 'queue') {
    return (
      <>
        <PageTitle title="Triage Queue" subtitle="Clinic queue — check-in, vitals, and nurse overtake" />
        <div className="grid gap-6 xl:grid-cols-3">
          <section><h2 className="mb-4 font-extrabold uppercase tracking-[0.12em] text-[#526783]">Waiting <Pill tone="slate">3</Pill></h2>{['Blessing Etim|SV-00821 · 5 min|URGENT', 'Samuel Udofia|SV-00819 · 22 min|MODERATE', 'Grace Nwachukwu|SV-00817 · 38 min|LOW'].map((row) => { const [name, meta, urgency] = row.split('|'); return <Card key={name} className="mb-3 p-5"><div className="flex justify-between"><h3 className="font-black">{name}</h3><Pill tone={urgency === 'URGENT' ? 'urgent' : urgency === 'LOW' ? 'slate' : 'routine'}>{urgency}</Pill></div><p className="mt-3 text-[#8a97b4]">{meta}</p><div className="mt-4 flex gap-2"><button className="rounded-xl border border-[#a9b3ff] px-4 py-2 font-bold text-[#6157f5]">Check-in</button><button className="rounded-xl border border-[#dbe3ef] px-4 py-2 font-bold">Vitals</button><button className="rounded-xl bg-[#2563EB] px-4 py-2 font-bold text-white">Overtake</button></div></Card>; })}</section>
          <section><h2 className="mb-4 font-extrabold uppercase tracking-[0.12em] text-[#526783]">Being Seen <Pill tone="slate">1</Pill></h2><Card className="border-[#2563EB] p-5"><div className="flex justify-between"><h3 className="font-black">Peter Akpan</h3><span className="h-2.5 w-2.5 rounded-full bg-[#60A5FA]" /></div><p className="mt-4 text-[#8a97b4]">SV-00814 · Dr. Effiong</p><button className="mt-4 rounded-xl border border-blue-200 px-4 py-2 font-bold text-[#2563EB]">Mark done</button></Card></section>
          <section><h2 className="mb-4 font-extrabold uppercase tracking-[0.12em] text-[#526783]">Done <Pill tone="slate">2</Pill></h2>{['Chinwe Obi|Done 9:42 AM', 'Musa Ibrahim|Done 10:18 AM'].map((row) => { const [name, meta] = row.split('|'); return <div key={name} className="mb-4 rounded-[18px] border border-dashed border-[#dbe3ef] p-5"><h3 className="font-black text-[#526783]">{name}</h3><p className="mt-2 text-sm text-[#8a97b4]">{meta}</p></div>; })}</section>
        </div>
      </>
    );
  }

  if (view === 'visits') {
    return (
      <>
        <PageTitle title="Home Visits" />
        <GoogleMapEmbed title="Uyo LGA visit route map" query="Uyo Akwa Ibom Nigeria" caption="3 visits · ~12 km total" className="mb-6" />
        <div className="space-y-5">{[
          ['Adaeze Chukwu', '12 Ikot Ekpene Rd, Uyo', '2:00 PM · Post-op check', 'UPCOMING'],
          ['Chief Akpan Udo', '8 Aba Rd, Uyo', '4:30 PM · CHF monitoring', 'UPCOMING'],
          ['Mama Ngozi Obi', '33 Calabar St, Uyo', '9:00 AM · Diabetes review', 'DONE'],
        ].map(([name, address, meta, status]) => <Card key={name} className="flex items-center justify-between"><div className="flex items-center gap-5"><span className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50">📍</span><div><h3 className="text-xl font-black">{name}</h3><p className="text-[#526783]">{address}</p><p className={status === 'DONE' ? 'text-[#2563EB]' : 'text-[#2563EB]'}>{meta}</p></div></div><div className="flex gap-3"><Pill tone={status === 'DONE' ? 'success' : 'urgent'}>{status}</Pill><Link href={status === 'DONE' ? '/nurse/care-plans' : '/nurse/visits'} className="rounded-xl bg-[#2563EB] px-5 py-3 font-bold text-white">{status === 'DONE' ? 'View report' : 'Start visit'}</Link><a href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${address}, Uyo, Akwa Ibom, Nigeria`)}`} target="_blank" rel="noreferrer" className="rounded-xl border border-[#dbe3ef] px-5 py-3 font-bold">Navigate</a></div></Card>)}</div>
      </>
    );
  }

  if (view === 'patients') {
    return (
      <>
        <PageTitle title="My Patients" action={<div className="rounded-xl bg-slate-100 px-6 py-3 text-[#8a97b4]">🔍 Search patients...</div>} />
        <div className="space-y-5">
          {[
            ['AC', 'Adaeze Chukwu', 'SV-00412 · Post-op hypertension', 'Next: Today, 2:00 PM', '140/90', '97%', 'STABLE'],
            ['MN', 'Mama Ngozi Obi', 'SV-00398 · Diabetes management', 'Next: Today, 4:00 PM', '130/85', '99%', 'STABLE'],
            ['CA', 'Chief Akpan Udo', 'SV-00371 · CHF monitoring', 'Next: Tomorrow, 10:00 AM', '155/100', '94%', 'WATCH'],
            ['AU', 'Amaka Uwah', 'SV-00356 · Post-partum care', 'Next: Thu, 9:00 AM', '118/76', '99%', 'STABLE'],
          ].map(([initials, name, detail, next, bp, spo2, status]) => <Card key={name} className="flex flex-wrap items-center justify-between gap-5"><div className="flex items-center gap-5"><div className="grid h-14 w-14 place-items-center rounded-xl bg-[#2563EB] text-lg font-black text-white">{initials}</div><div><h3 className="text-xl font-black">{name}</h3><p className="text-[#526783]">{detail}</p><p className="text-[#8a97b4]">{next}</p></div></div><div className="flex items-center gap-3"><div className="rounded-xl bg-slate-50 px-4 py-3 text-center"><p className="text-xs text-[#8a97b4]">BP</p><b className={status === 'WATCH' ? 'text-rose-500' : ''}>{bp}</b></div><div className="rounded-xl bg-slate-50 px-4 py-3 text-center"><p className="text-xs text-[#8a97b4]">SpO2</p><b className={status === 'WATCH' ? 'text-rose-500' : ''}>{spo2}</b></div><Link href="/nurse/vitals" className="rounded-xl border border-[#dbe3ef] px-5 py-3 font-bold">Log vitals</Link><Link href="/nurse/care-plans" className="rounded-xl border border-[#dbe3ef] px-5 py-3 font-bold">Care plan</Link><Pill tone={status === 'WATCH' ? 'urgent' : 'success'}>{status}</Pill></div></Card>)}
        </div>
      </>
    );
  }

  if (view === 'schedule') {
    return (
      <>
        <PageTitle title="My Schedule" />
        <Card><div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-black">Week of June 16–22, 2026</h2><div className="flex gap-3"><button className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">← Prev</button><button className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">Next →</button></div></div><div className="grid gap-4 xl:grid-cols-5">{['Mon 16|9:00–12:00|Clinic duty', 'Tue 17|10:00 Mama Ngozi|2:30 Chief Akpan', 'Wed 18|8:00–16:00|Clinic duty', 'Thu 19|9:00 Amaka Uwah|', 'Fri 20|2:00 Adaeze|4:30 Chief Akpan'].map((day) => { const [label, a, b] = day.split('|'); return <div key={label} className={`rounded-[14px] bg-slate-50 p-4 ${label === 'Fri 20' ? 'border-2 border-[#2563EB] bg-blue-50' : ''}`}><h3 className="mb-4 font-black text-[#526783]">{label}</h3><p className="rounded-lg border border-[#dbe3ef] bg-white p-3">{a}</p>{b ? <p className="mt-2 rounded-lg border border-[#dbe3ef] bg-white p-3">{b}</p> : null}</div>; })}</div></Card>
      </>
    );
  }

  if (view === 'vitals') {
    return (
      <>
        <PageTitle title="Vitals Entry" subtitle="Enter and save patient vital signs" />
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.7fr]">
          <Card><h2 className="mb-5 text-lg font-black">Select Patient</h2>{['AC|Adaeze Chukwu|Post-op hypertension', 'MN|Mama Ngozi Obi|Diabetes management', 'CA|Chief Akpan Udo|CHF monitoring', 'AU|Amaka Uwah|Post-partum care'].map((row) => { const [initials, name, detail] = row.split('|'); return <div key={name} className={`mb-3 flex items-center gap-4 rounded-xl border p-4 ${initials === 'CA' ? 'border-[#2563EB] bg-blue-50' : 'border-[#dbe3ef]'}`}><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#2563EB] font-black text-white">{initials}</span><div><h3 className="font-black">{name}</h3><p className="text-sm text-[#8a97b4]">{detail}</p></div></div>; })}</Card>
          <Card><h2 className="mb-6 text-xl font-black">Chief Akpan Udo — Vitals</h2><div className="grid gap-5 md:grid-cols-3">{['Blood Pressure ⚠|155/100|mmHg|warn', 'Temperature|37.4|°C|', 'SpO2 ⚠|94|%|warn', 'Pulse|96|bpm|', 'Weight|68|kg|', 'Respiratory Rate|18|/min|'].map((item) => { const [label, value, unit, warn] = item.split('|'); return <div key={label} className={`rounded-[14px] p-5 ${warn ? 'border border-amber-300 bg-amber-50 text-rose-600' : 'bg-slate-50'}`}><p className="text-sm text-[#8a97b4]">{label}</p><p className="mt-4 text-3xl font-black">{value} <span className="text-sm font-normal text-[#8a97b4]">{unit}</span></p></div>; })}</div><label className="mt-6 block"><span className="font-bold">Notes</span><textarea readOnly value="Patient reports mild dizziness on standing." className="mt-2 min-h-20 w-full rounded-xl border border-[#dbe3ef] p-4 text-lg outline-none" /></label><div className="mt-6 flex gap-3"><button className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Save Vitals</button><button className="rounded-xl border border-rose-200 px-6 py-3 font-bold text-rose-500">🚨 Flag to Doctor</button></div></Card>
        </div>
      </>
    );
  }

  if (view === 'care-plans') {
    return (
      <>
        <PageTitle title="Care Plans" action={<div className="flex gap-3"><button className="rounded-full bg-[#2563EB] px-6 py-3 font-bold text-white">Active</button><button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3">Review</button><button className="rounded-full border border-[#dbe3ef] bg-white px-6 py-3">Completed</button></div>} />
        <div className="space-y-5">{([
          ['Adaeze Chukwu', 'Post-op hypertension', 'ON TRACK', 'Today, 2:00 PM', false],
          ['Mama Ngozi Obi', 'Diabetes management', 'ON TRACK', 'Today, 4:00 PM', false],
          ['Chief Akpan Udo', 'CHF monitoring', 'REVIEW NEEDED', 'Tomorrow, 10:00 AM', true],
          ['Amaka Uwah', 'Post-partum care', 'ON TRACK', 'Thu, 9:00 AM', false],
        ] as const).map(([name, condition, status, next, urgent]) => <Card key={name}><div className="flex justify-between"><div><h3 className="text-xl font-black">{name}</h3><p className="text-[#526783]">{condition}</p></div><Pill tone={urgent ? 'urgent' : 'success'}>{status}</Pill></div><div className="mt-6 grid gap-4 rounded-xl bg-slate-50 p-4 md:grid-cols-3"><div><p className="text-sm text-[#8a97b4]">Last visit</p><b>June 18, 2026</b></div><div><p className="text-sm text-[#8a97b4]">Next visit</p><b>{next}</b></div><div><p className="text-sm text-[#8a97b4]">Visit count</p><b>7 total</b></div></div><div className="mt-5 flex gap-3"><Link href="/nurse/care-plans" className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">View plan</Link><Link href="/nurse/care-plans" className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">Add note</Link>{urgent ? <Link href="/nurse/care-plans" className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Update urgently</Link> : null}</div></Card>)}</div>
      </>
    );
  }

  if (view === 'notifications') {
    return (
      <>
        <PageTitle title="Notifications" />
        <Card>{['Critical vitals: Chief Akpan Udo — SpO2 94%. Flagged to Dr. Effiong|45 min ago|bg-rose-500', 'New patient assignment: Grace Nwachukwu — Post-partum follow-up|2 hours ago|bg-[#6157f5]', 'Visit reminder: Adaeze Chukwu — Today at 2:00 PM|3 hours ago|bg-[#2563EB]', 'Care plan updated successfully: Mama Ngozi Obi|4 hours ago|bg-[#2563EB]', 'Weekly vitals report ready for download|Yesterday|bg-slate-400'].map((row) => { const [text, time, dot] = row.split('|'); return <div key={text} className="flex justify-between border-b border-slate-100 py-5 last:border-0"><div><h3 className="font-bold text-[#12284a]">{text}</h3><p className="mt-1 text-[#8a97b4]">{time}</p></div><span className={`h-2.5 w-2.5 rounded-full ${dot}`} /></div>; })}</Card>
      </>
    );
  }

  if (view === 'settings') {
    return (
      <>
        <PageTitle title="Settings" />
        <div className="grid gap-6 xl:grid-cols-2">
          <Card><h2 className="mb-6 text-xl font-black">Profile</h2><div className="space-y-5"><TextField label="Full name" value="Blessing Effiong" /><TextField label="NMCN Number" value="NMCN-2019-04821" /><TextField label="Specialty" value="Community Health Nursing" /><TextField label="Phone" value="+234 805 123 4567" /></div><button className="mt-5 rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Save profile</button></Card>
          <Card><h2 className="mb-6 text-xl font-black">Availability</h2><div className="space-y-5"><TextField label="Work type" value="Community Nurse" /><TextField label="Active hours" value="7:00 AM – 5:00 PM" /><TextField label="Coverage area" value="Uyo LGA, Akwa Ibom" /></div><h3 className="mt-6 font-black">Notifications</h3>{['New patient assignment', 'Critical vitals alerts', 'Visit reminders', 'Schedule changes'].map((item) => <div key={item} className="mt-4 flex justify-between text-lg"><span>{item}</span><span className="grid h-5 w-5 place-items-center rounded bg-[#2563EB] text-white">✓</span></div>)}<button className="mt-6 rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Save settings</button></Card>
        </div>
      </>
    );
  }

  return (
    <>
      <PageTitle title="Good afternoon, Blessing" subtitle="Friday, 20 June 2026 · Community Nurse · Uyo LGA" />
      <StatGrid stats={[
        { title: 'Patients Today', value: '4', sub: '2 visits remaining', tone: 'sky' },
        { title: 'Vitals Logged', value: '6', sub: '1 critical flag', tone: 'amber' },
        { title: 'Care Plans Active', value: '12', sub: '1 needs update', tone: 'slate' },
        { title: 'Visits Done', value: '1/3', sub: 'Today', tone: 'sky' },
      ]} />
      <div className="mt-8 grid gap-6 xl:grid-cols-[1.6fr_0.9fr]">
        <Card><div className="mb-6 flex items-center justify-between"><h2 className="text-xl font-black">Today's Visits</h2><Link href="/nurse/visits" className="rounded-xl border border-[#dbe3ef] px-6 py-3 font-bold">Full map →</Link></div>{[
          ['Adaeze Chukwu', '12 Ikot Ekpene Rd, Uyo', '2:00 PM · Post-op check', 'UPCOMING'],
          ['Chief Akpan Udo', '8 Aba Rd, Uyo', '4:30 PM · CHF monitoring', 'UPCOMING'],
          ['Mama Ngozi Obi', '33 Calabar St, Uyo', '9:00 AM · Diabetes review', 'DONE'],
        ].map(([name, address, meta, status]) => <div key={name} className="flex items-center justify-between border-b border-slate-100 py-5 last:border-0"><div className="flex items-center gap-5"><span className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50">📍</span><div><h3 className="text-lg font-black">{name}</h3><p className="text-[#8a97b4]">{address}</p><p className={status === 'DONE' ? 'text-[#2563EB]' : 'text-[#2563EB]'}>{meta}</p></div></div><Pill tone={status === 'DONE' ? 'success' : 'urgent'}>{status}</Pill></div>)}</Card>
        <Card><h2 className="mb-6 text-xl font-black">Critical Flags</h2><section className="rounded-[14px] border border-amber-300 bg-amber-50 p-5 text-[#9a3412]"><h3 className="font-black">⚠ Abnormal Vitals</h3><p className="mt-3">Chief Akpan Udo — SpO2 94%, BP 155/100</p><p className="mt-3">Flagged to Dr. Effiong</p></section><section className="mt-4 rounded-[14px] border border-blue-200 bg-blue-50 p-5 text-[#0369a1]"><h3 className="font-black">✓ Care plan updated</h3><p className="mt-3">Mama Ngozi Obi — Diabetes plan reviewed</p><p className="mt-3">4 hours ago</p></section></Card>
      </div>
      <Card className="mt-6"><div className="mb-5 flex items-center justify-between"><h2 className="text-xl font-black">Quick Vitals Entry</h2><div className="flex gap-2"><button className="rounded-full border border-[#dbe3ef] px-5 py-2">Adaeze</button><button className="rounded-full border border-[#dbe3ef] px-5 py-2">Mama</button><button className="rounded-full bg-[#2563EB] px-5 py-2 font-bold text-white">Chief</button></div></div><div className="grid gap-4 md:grid-cols-5">{['Blood Pressure|155/100 mmHg', 'Temperature|37.4 °C', 'SpO2|94 %', 'Pulse|96 bpm', 'Weight|68 kg'].map((item) => { const [label, value] = item.split('|'); return <div key={label} className="rounded-xl bg-slate-50 p-4"><p className="text-sm text-[#8a97b4]">{label}</p><b className={`text-2xl ${value.includes('94') ? 'text-rose-500' : ''}`}>{value}</b></div>; })}</div><div className="mt-5 flex gap-3"><Link href="/nurse/vitals" className="rounded-xl bg-[#2563EB] px-6 py-3 font-bold text-white">Log Vitals</Link><button className="rounded-xl border border-rose-200 px-6 py-3 font-bold text-rose-500">Flag Critical</button></div></Card>
    </>
  );
}

function GenericDashboard({ entity, view, title, subtitle }: { entity: EntityKey; view: View; title: string; subtitle?: string }) {
  const data = dashboardEntities[entity];
  return <><PageTitle title={title} subtitle={subtitle} /><StatGrid stats={data.stats.slice(0, 4)} />{view === 'settings' ? <div className="mt-8"><SettingsRows rows={[['Name', data.identity.name], ['Workspace', data.identity.subtitle], ['Status', 'Active']]}/></div> : <div className="mt-8"><DataTable columns={data.table.columns} rows={data.table.rows} /></div>}</>;
}

export function EntityDashboard({ entity: entityKey, view, title, subtitle }: EntityDashboardProps) {
  const entity = dashboardEntities[entityKey];
  const resolvedTitle = title ?? 'Overview';
  const body =
    entityKey === 'specialist' ? <DoctorDashboard view={view} /> :
    entityKey === 'hospital' ? <HospitalDashboard view={view} /> :
    entityKey === 'pharmacy' ? <PharmacyDashboard view={view} /> :
    entityKey === 'admin' ? <AdminDashboard view={view} /> :
    entityKey === 'lab' ? <LabDashboard view={view} /> :
    entityKey === 'hmo' ? <HmoDashboard view={view} /> :
    entityKey === 'moh' ? <MohDashboard view={view} /> :
    entityKey === 'clinic' ? <ClinicDashboard view={view} /> :
    entityKey === 'nurse' ? <NurseDashboard view={view} /> :
    <GenericDashboard entity={entityKey} view={view} title={resolvedTitle} subtitle={subtitle} />;

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      {body}
    </DashboardShell>
  );
}
