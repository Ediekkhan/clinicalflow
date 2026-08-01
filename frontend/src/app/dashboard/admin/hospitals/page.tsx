 'use client';

import { useEffect, useState } from 'react';
import { Check, Loader2, X } from 'lucide-react';
import { EntityDashboard } from '@/components/entity/EntityDashboard';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';

type Application = { id: string; reference: string; status: string; organization_name?: string; email?: string; phone?: string; country?: string; latitude?: number; longitude?: number; submitted_at?: string };

export default function AdminHospitalsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true); setError('');
    try { const response = await api.get('/api/v1/platform/signup-applications') as { items?: Application[] }; setApplications(Array.isArray(response.items) ? response.items : []); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to load hospital applications.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function review(id: string, decision: 'APPROVE' | 'REJECT') {
    setBusyId(id); setError('');
    try { await api.patch(`/api/v1/platform/signup-applications/${id}/review`, { decision }); setApplications((current) => current.map((item) => item.id === id ? { ...item, status: decision === 'APPROVE' ? 'ACTIVE' : 'REJECTED' } : item)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to review this application.'); }
    finally { setBusyId(null); }
  }
  const pending = applications.filter((item) => item.status === 'PENDING_FACILITY_VERIFICATION');
  return <EntityDashboard entity="admin" view="facilities" title="Hospital approvals" subtitle="Review registered hospital applications before activation.">
    {error ? <p role="alert" className="mb-5 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p> : null}
    {loading ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-28 animate-pulse rounded-2xl bg-slate-100" />)}</div> : pending.length === 0 ? <EmptyState title="No pending hospital applications" body="New facility registrations will appear here for review." /> : <div className="space-y-4">{pending.map((item) => <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-lg font-bold text-slate-900">{item.organization_name || 'Unnamed hospital'}</h2><p className="mt-1 text-sm text-slate-500">{item.reference} · {item.email || item.phone || 'No contact provided'}</p><p className="mt-2 text-xs text-slate-500">{item.country || 'Country not provided'}{item.latitude !== undefined && item.longitude !== undefined ? ` · ${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}` : ''}</p></div><span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">Pending review</span></div><div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={busyId === item.id} onClick={() => void review(item.id, 'APPROVE')} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"><Check className="h-4 w-4" />{busyId === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Approve hospital'}</button><button type="button" disabled={busyId === item.id} onClick={() => void review(item.id, 'REJECT')} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-rose-200 px-4 py-2 text-sm font-bold text-rose-700 disabled:opacity-50"><X className="h-4 w-4" />Reject</button></div></article>)}</div>}
  </EntityDashboard>;
}
