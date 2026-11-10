'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import SiteLayout from '@/components/layout/SiteLayout';
import { api } from '@/lib/auth';

const fields = [
  ['organization_legal_name', 'Organization legal name', 'text'], ['organization_type', 'Organization type', 'select'],
  ['country', 'Country', 'text'], ['operations', 'States, regions or countries of operation', 'textarea'],
  ['contact_name', 'Contact person full name', 'text'], ['job_title', 'Job title', 'text'], ['official_work_email', 'Official work email', 'email'],
  ['telephone', 'Telephone number', 'tel'], ['website', 'Organization website', 'url'], ['facility_count', 'Number of facilities', 'number'],
  ['staff_count', 'Estimated staff count', 'number'], ['monthly_patient_volume', 'Estimated monthly patient volume', 'number'],
  ['current_system', 'Current healthcare information system', 'text'], ['integrations', 'Required integrations', 'textarea'],
  ['dashboards', 'Required dashboards', 'textarea'], ['security_requirements', 'Security requirements', 'textarea'],
  ['compliance_requirements', 'Compliance and data-hosting requirements', 'textarea'], ['deployment_model', 'Preferred deployment model', 'text'],
  ['preferred_pilot_date', 'Preferred pilot date', 'date'], ['expected_rollout_date', 'Expected rollout date', 'date'],
  ['budget_range', 'Budget range (optional)', 'text'], ['additional_message', 'Additional message', 'textarea'],
  ['preferred_contact_method', 'Preferred contact method', 'text'], ['preferred_meeting_date', 'Preferred meeting date', 'date'], ['meeting_timezone', 'Meeting timezone', 'text'],
] as const;

const initial = Object.fromEntries(fields.map(([name]) => [name, ''])) as Record<string, string>;

export default function ContactSalesPage() {
  const router = useRouter();
  const [form, setForm] = useState(initial);
  const [status, setStatus] = useState<'idle' | 'saving' | 'error'>('idle');
  const [consent, setConsent] = useState(false);
  useEffect(() => { void api.get('/api/v1/auth/hospital_admin/me').then((profile) => { const value = profile as { first_name?: string; last_name?: string; email?: string; phone?: string }; setForm(current => ({ ...current, contact_name: [value.first_name, value.last_name].filter(Boolean).join(' '), official_work_email: value.email ?? '', telephone: value.phone ?? '' })); }).catch(() => undefined); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!consent) return;
    setStatus('saving');
    try {
      const result = await api.post('/api/v1/public/enterprise-enquiries', { ...form, consent_to_contact: consent, plan: 'enterprise' }, { headers: { 'x-idempotency-key': crypto.randomUUID() } }) as { reference: string };
      router.push(`/contact-sales/success?reference=${encodeURIComponent(result.reference)}`);
    } catch { setStatus('error'); }
  }

  return <main className="bg-slate-50 text-[#10231e]"><SiteLayout><section className="px-6 pb-24 pt-32"><form onSubmit={submit} className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-10"><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Enterprise</p><h1 className="font-display mt-3 text-4xl">Talk with ClinicalFlow sales</h1><p className="mt-3 max-w-2xl leading-7 text-slate-600">Tell us about your organization and rollout goals. You can review every field before submitting.</p><div className="mt-8 grid gap-5 sm:grid-cols-2">{fields.map(([name, label, type]) => <label key={name} className={type === 'textarea' ? 'sm:col-span-2' : ''}><span className="text-sm font-semibold text-slate-700">{label}</span>{type === 'textarea' ? <textarea required={name === 'operations' || name === 'additional_message'} value={form[name]} onChange={e => setForm({ ...form, [name]: e.target.value })} rows={3} className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3" /> : type === 'select' ? <select required value={form[name]} onChange={e => setForm({ ...form, [name]: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3"><option value="">Select organization type</option>{['Hospital','Hospital network','Clinic network','Pharmacy network','Laboratory network','HMO or insurer','Government health agency','Public-health programme','NGO or international health organization','Healthcare technology partner'].map(option => <option key={option}>{option}</option>)}</select> : <input required={['organization_legal_name','country','contact_name','official_work_email'].includes(name)} type={type} value={form[name]} onChange={e => setForm({ ...form, [name]: e.target.value })} className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3" />}</label>)}</div><label className="mt-6 flex items-start gap-3 text-sm text-slate-700"><input required type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} className="mt-1" />I consent to be contacted about ClinicalFlow Enterprise.</label>{status === 'error' ? <p className="mt-5 rounded-xl bg-rose-50 p-4 text-sm font-semibold text-rose-700">We could not submit your enquiry. Please try again.</p> : null}<button disabled={status === 'saving' || !consent} className="mt-6 min-h-12 rounded-xl bg-[#0b5d4b] px-6 py-3 font-bold text-white disabled:opacity-60">{status === 'saving' ? 'Submitting…' : 'Submit enquiry'}</button></form></section></SiteLayout></main>;
}
