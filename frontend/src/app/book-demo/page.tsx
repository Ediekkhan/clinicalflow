'use client';

import { useState } from 'react';
import SiteLayout from '@/components/layout/SiteLayout';
import { api } from '@/lib/auth';

export default function BookDemoPage() {
  const [form, setForm] = useState({ organization_name: '', work_email: '', phone: '', facility_type: '' });
  const [status, setStatus] = useState<'idle' | 'saving' | 'done' | 'error'>('idle');

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus('saving');
    try {
      await api.post('/api/v1/public/demo-requests', { ...form, source: 'WEBSITE' });
      setStatus('done');
    } catch {
      setStatus('error');
    }
  }

  const fields = [
    ['organization_name', 'Organization name', 'text'],
    ['work_email', 'Work email', 'email'],
    ['phone', 'Phone number', 'tel'],
    ['facility_type', 'Facility type', 'text'],
  ] as const;

  return (
    <main className="bg-slate-50">
      <SiteLayout>
        <section className="grid min-h-screen place-items-center px-6 py-32">
          <form onSubmit={submit} className="w-full max-w-xl rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Book a Demo</p>
            <h1 className="font-display mt-2 text-4xl text-slate-900">See ClinicalFlow in action</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">Tell us about your facility and our onboarding team will contact you.</p>
            {status === 'done' ? (
              <div className="mt-8 rounded-xl bg-emerald-50 p-6 text-center">
                <h2 className="text-xl font-bold text-emerald-800">Request received</h2>
                <p className="mt-2 text-sm text-emerald-700">We have saved your details and will follow up with your facility.</p>
              </div>
            ) : (
              <div className="mt-6 grid gap-4">
                {fields.map(([name, label, type]) => (
                  <label key={name} className="grid gap-1.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>
                    <input required={name === 'organization_name' || name === 'work_email'} type={type} value={form[name]} onChange={(event) => setForm((current) => ({ ...current, [name]: event.target.value }))} className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#0b5d4b] focus:ring-2 focus:ring-blue-100" placeholder={label} />
                  </label>
                ))}
                {status === 'error' ? <p className="text-sm font-semibold text-rose-600">Could not save your request. Please try again.</p> : null}
                <button disabled={status === 'saving'} className="rounded-xl bg-[#0b5d4b] px-5 py-3 text-sm font-semibold text-white disabled:bg-slate-300">{status === 'saving' ? 'Sending…' : 'Request Demo'}</button>
              </div>
            )}
          </form>
        </section>
      </SiteLayout>
    </main>
  );
}
