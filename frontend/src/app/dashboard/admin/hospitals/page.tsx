'use client';

import { useEffect, useState } from 'react';
import { Check, ClipboardCheck, Loader2, UserRound, X } from 'lucide-react';
import { EntityDashboard } from '@/components/entity/EntityDashboard';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';

type Verification = { id: string; application_id: string; reference: string; status: string; organization_name?: string; country?: string; priority?: string; review_due_at?: string; assigned_reviewer_id?: string | null; government_check_status?: string };

export default function AdminHospitalsPage() {
  const [items, setItems] = useState<Verification[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true); setError('');
    try { const response = await api.get('/api/v1/platform/facility-verifications') as { items?: Verification[] }; setItems(Array.isArray(response.items) ? response.items : []); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to load verification cases.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  async function act(item: Verification, action: 'assign' | 'request-information' | 'reject' | 'approve') {
    const id = item.id;
    setBusyId(id); setError('');
    try {
      const reason = action === 'request-information' ? window.prompt('What information is required?') : action === 'reject' ? window.prompt('Reason for rejection?') : null;
      if ((action === 'reject' || action === 'request-information') && !reason) return;
      if (action === 'reject' || action === 'approve') await api.patch(`/api/v1/platform/signup-applications/${item.application_id}/review`, { decision: action === 'approve' ? 'APPROVE' : 'REJECT', reason });
      else await api.post(`/api/v1/platform/facility-verifications/${id}/${action}`, reason ? { reason } : {});
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to update this verification case.'); }
    finally { setBusyId(null); }
  }

  return <EntityDashboard entity="admin" view="facilities" title="Hospital verification" subtitle="Review registry evidence and facility applications before operational activation.">
    {error ? <p role="alert" className="mb-5 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p> : null}
    {loading ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-28 animate-pulse rounded-2xl bg-slate-100" />)}</div> : items.length === 0 ? <EmptyState title="No verification cases" body="New hospital applications will appear here for review." /> : <div className="space-y-4">{items.map((item) => <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-lg font-bold text-slate-900">{item.organization_name || 'Unnamed hospital'}</h2><p className="mt-1 text-sm text-slate-500">{item.reference} · {item.country || 'Country not provided'}</p><p className="mt-2 text-xs text-slate-500">{item.review_due_at ? `Review due ${new Date(item.review_due_at).toLocaleDateString()}` : 'Review deadline pending'} · Registry: {item.government_check_status || 'PENDING'}</p></div><span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">{item.status}</span></div><div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={busyId === item.id} onClick={() => void act(item, 'assign')} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"><UserRound className="h-4 w-4" />Assign to me</button><button type="button" disabled={busyId === item.id} onClick={() => void act(item, 'request-information')} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-amber-200 px-4 py-2 text-sm font-bold text-amber-700 disabled:opacity-50"><ClipboardCheck className="h-4 w-4" />Request information</button><button type="button" disabled={busyId === item.id} onClick={() => void act(item, 'approve')} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-emerald-200 px-4 py-2 text-sm font-bold text-emerald-700 disabled:opacity-50"><Check className="h-4 w-4" />Approve setup</button><button type="button" disabled={busyId === item.id} onClick={() => void act(item, 'reject')} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-rose-200 px-4 py-2 text-sm font-bold text-rose-700 disabled:opacity-50"><X className="h-4 w-4" />Reject</button>{busyId === item.id ? <Loader2 className="h-5 w-5 animate-spin text-slate-400" /> : null}</div></article>)}</div>}
  </EntityDashboard>;
}
