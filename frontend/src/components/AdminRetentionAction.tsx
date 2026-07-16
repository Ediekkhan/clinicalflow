'use client';

import { useState } from 'react';
import { EntityDashboard } from '@/components/entity/EntityDashboard';
import { api } from '@/lib/auth';

type Result = { sessions_deleted: number; audit_logs_deleted: number; demo_leads_deleted: number };

export function AdminRetentionAction() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');

  async function runRetention() {
    setRunning(true); setError('');
    try {
      setResult(await api.post('/api/v1/admin/maintenance/retention', {}) as Result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Retention job failed.');
    } finally { setRunning(false); }
  }

  return (
    <EntityDashboard entity="admin" view="settings" title="Settings">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">Data retention</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Delete expired sessions, audit records, and demo leads according to the configured retention policy.</p>
        <button type="button" disabled={running} onClick={runRetention} className="mt-4 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-60">{running ? 'Running…' : 'Run retention now'}</button>
        {result ? <p className="mt-3 text-sm text-slate-600" role="status">Deleted {result.sessions_deleted} sessions, {result.audit_logs_deleted} audit records, and {result.demo_leads_deleted} demo leads.</p> : null}
        {error ? <p className="mt-3 text-sm text-rose-600" role="alert">{error}</p> : null}
      </section>
    </EntityDashboard>
  );
}
