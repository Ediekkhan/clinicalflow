'use client';

import { Building2, Check, ChevronDown, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '@/lib/auth';

type Workspace = { id: string; hospital_name?: string | null; department_name: string; role: string; state: string; selected: boolean };

export function WorkspaceSelector() {
  const [items, setItems] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState('');
  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/staff/workspaces').then((value) => { if (!cancelled && Array.isArray(value)) setItems(value as Workspace[]); }).catch(() => { if (!cancelled) setItems([]); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);
  async function selectWorkspace(id: string) {
    setSwitching(id);
    try { await api.post(`/api/v1/staff/workspaces/${id}/select`, {}); window.location.reload(); }
    finally { setSwitching(''); }
  }
  if (loading) return <div className="mb-5 h-12 w-full animate-pulse rounded-lg bg-slate-200 sm:w-80" />;
  if (items.length === 0 || (items.length === 1 && items[0].state === 'MEMBERSHIP_ACTIVE')) return null;
  const selected = items.find((item) => item.selected);
  return <details className="relative mb-6 w-full max-w-md rounded-lg border border-slate-200 bg-white shadow-sm">
    <summary className="flex min-h-12 cursor-pointer list-none items-center gap-3 px-4 py-3 text-sm font-semibold"><Building2 className="h-4 w-4 text-emerald-700" /><span className="min-w-0 flex-1 truncate">{selected ? `${selected.hospital_name ?? 'Facility'} · ${selected.department_name}` : 'Select your active workspace'}</span><ChevronDown className="h-4 w-4 text-slate-400" /></summary>
    <div className="border-t border-slate-100 p-2">{items.map((item) => { const active = item.state === 'MEMBERSHIP_ACTIVE'; return <button key={item.id} type="button" disabled={!active || switching.length > 0} onClick={() => void selectWorkspace(item.id)} className="flex min-h-14 w-full items-center gap-3 rounded-md px-3 py-2 text-left hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60">{switching === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : item.selected ? <Check className="h-4 w-4 text-emerald-700" /> : <span className="h-4 w-4" />}<span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{item.hospital_name ?? 'Facility'} · {item.department_name}</span><span className="block text-xs text-slate-500">{item.role.replaceAll('_', ' ')} · {item.state.replaceAll('_', ' ').toLowerCase()}</span></span></button>; })}</div>
  </details>;
}