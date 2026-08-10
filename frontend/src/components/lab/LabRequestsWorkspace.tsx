'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, FlaskConical } from 'lucide-react';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';
import { dashboardEntities } from '@/lib/dashboard-data';

type OrderedTest = { id: string; display: string; test_code: string; loinc_code?: string | null; status: string };
type LabOrder = { id: string; title: string; description?: string; status: string; created_at: string; tests: OrderedTest[] };

const entity = dashboardEntities.lab;

export function LabRequestsWorkspace() {
  const [orders, setOrders] = useState<LabOrder[]>([]);
  const [selected, setSelected] = useState<LabOrder | null>(null);
  const [specimenType, setSpecimenType] = useState('');
  const [resultValue, setResultValue] = useState('');
  const [critical, setCritical] = useState(false);
  const [conclusion, setConclusion] = useState('');
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/v1/lab/requests') as { items?: LabOrder[] };
      const items = Array.isArray(response?.items) ? response.items : [];
      setOrders(items);
      setSelected((current) => items.find((item) => item.id === current?.id) ?? null);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Unable to load laboratory requests.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setFeedback('');
    try { await action(); setFeedback(success); await load(); }
    catch (error) { setFeedback(error instanceof Error ? error.message : 'Unable to update this request.'); }
    finally { setBusy(false); }
  }

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <header className="mb-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Laboratory workflow</p>
        <h1 className="font-display mt-2 text-4xl text-[#10231e] sm:text-5xl">Test Requests</h1>
        <p className="mt-3 max-w-3xl text-slate-500">Accept orders, record collection, enter results, complete quality review, and release finalized reports.</p>
      </header>
      {feedback ? <div role="status" className="mb-5 flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700"><AlertCircle className="h-4 w-4" />{feedback}</div> : null}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,.7fr)]">
        <section>
          {loading ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-slate-100" />)}</div> : orders.length === 0 ? <EmptyState icon={FlaskConical} title="No test requests" body="Incoming laboratory orders will appear here." /> : (
            <div className="grid gap-3">
              {orders.map((order) => <button key={order.id} type="button" onClick={() => setSelected(order)} className={`min-h-24 rounded-xl border bg-white p-4 text-left transition ${selected?.id === order.id ? 'border-[#0b5d4b] shadow-md' : 'border-slate-200 hover:border-slate-300'}`}><div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{order.title}</p><p className="mt-1 text-sm text-slate-500">{order.tests.map((test) => test.display).join(', ')}</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{order.status.replaceAll('_', ' ')}</span></div></button>)}
            </div>
          )}
        </section>
        <aside className="border-t border-slate-200 pt-6 xl:border-l xl:border-t-0 xl:pl-6 xl:pt-0">
          {!selected ? <EmptyState icon={CheckCircle2} title="Select a request" body="Choose an order to view available workflow actions." /> : (
            <div className="space-y-5">
              <div><h2 className="text-xl font-bold text-slate-900">{selected.title}</h2><p className="mt-1 text-sm text-slate-500">Current state: {selected.status.replaceAll('_', ' ')}</p></div>
              {selected.status === 'REQUESTED' ? <button disabled={busy} onClick={() => void run(() => api.post(`/api/v1/laboratory/orders/${selected.id}/accept`, {}), 'Order accepted.')} className="sv-button-dark w-full">Accept order</button> : null}
              {['ACCEPTED', 'COLLECTION_SCHEDULED', 'RECOLLECTION_REQUIRED'].includes(selected.status) ? <div className="space-y-3"><label className="block text-sm font-semibold text-slate-700">Specimen type<input value={specimenType} onChange={(event) => setSpecimenType(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3" placeholder="e.g. Blood" /></label><button disabled={busy || !specimenType.trim()} onClick={() => void run(() => api.post(`/api/v1/laboratory/orders/${selected.id}/specimens`, { specimen_type: specimenType }), 'Collection recorded.')} className="sv-button-dark w-full">Record collection</button></div> : null}
              {['SPECIMEN_COLLECTED', 'RESULTS_PENDING_REVIEW'].includes(selected.status) && selected.tests[0] ? <div className="space-y-3"><label className="block text-sm font-semibold text-slate-700">Result for {selected.tests[0].display}<input value={resultValue} onChange={(event) => setResultValue(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3" placeholder="Enter result" /></label><label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={critical} onChange={(event) => setCritical(event.target.checked)} />Critical result</label><button disabled={busy || !resultValue.trim()} onClick={() => void run(() => api.post(`/api/v1/laboratory/orders/${selected.id}/results`, { ordered_test_id: selected.tests[0].id, value: resultValue, is_critical: critical, status: 'PRELIMINARY' }), 'Result recorded for quality review.')} className="sv-button-dark w-full">Save result</button></div> : null}
              {selected.status === 'RESULTS_PENDING_REVIEW' ? <div className="space-y-3"><label className="block text-sm font-semibold text-slate-700">Report conclusion<textarea value={conclusion} onChange={(event) => setConclusion(event.target.value)} rows={3} className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3" /></label><button disabled={busy} onClick={() => void run(() => api.post(`/api/v1/laboratory/orders/${selected.id}/finalize`, { decision: 'APPROVED', conclusion }), 'Report finalized.')} className="sv-button-dark w-full">Approve final report</button></div> : null}
              {selected.status === 'FINAL' ? <button disabled={busy} onClick={() => void run(() => api.post(`/api/v1/laboratory/orders/${selected.id}/release`, {}), 'Report released to the patient.')} className="sv-button-dark w-full">Release to patient</button> : null}
            </div>
          )}
        </aside>
      </div>
    </DashboardShell>
  );
}
