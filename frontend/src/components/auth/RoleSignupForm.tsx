'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Check, Loader2, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import { api } from '@/lib/auth';
import type { SignupConfig, SignupField } from '@/lib/signup-config';

type Values = Record<string, string>;
type SignupResponse = { id: string; reference: string; status: string };

const topLevelFields = new Set(['first_name', 'middle_name', 'last_name', 'full_name', 'phone', 'email', 'country', 'region', 'password', 'confirm_password', 'invitation_token']);

function inputClass(hasError: boolean) {
  return `min-h-12 w-full rounded-xl border bg-white px-4 py-3 text-sm text-[#10231e] outline-none transition ${hasError ? 'border-rose-400 focus:ring-2 focus:ring-rose-100' : 'border-[#dbe2dc] focus:border-[#0b5d4b] focus:ring-2 focus:ring-[#e9f6f1]'}`;
}

function validateField(field: SignupField, value: string) {
  const trimmed = value.trim();
  if (field.required && !trimmed) return `${field.label} is required.`;
  if (!trimmed) return '';
  if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return 'Enter a valid email address.';
  if (field.type === 'tel' && !/^\+[1-9]\d{7,14}$/.test(trimmed.replace(/[\s()-]/g, ''))) return 'Include the international country code, for example +234.';
  if (field.name === 'password' && (trimmed.length < 8 || !/[A-Z]/.test(trimmed) || !/\d/.test(trimmed))) return 'Use at least 8 characters, one uppercase letter and one number.';
  if (field.type === 'number') {
    const number = Number(trimmed);
    if (!Number.isFinite(number)) return 'Enter a valid number.';
    if (field.min !== undefined && number < field.min) return `Minimum value is ${field.min}.`;
    if (field.max !== undefined && number > field.max) return `Maximum value is ${field.max}.`;
  }
  return '';
}

function FieldControl({ field, value, error, onChange }: { field: SignupField; value: string; error?: string; onChange: (value: string) => void }) {
  const id = `signup-${field.name}`;
  const describedBy = error ? `${id}-error` : undefined;
  return (
    <label className={field.type === 'textarea' ? 'grid gap-2 sm:col-span-2' : 'grid gap-2'} htmlFor={id}>
      <span className="text-sm font-bold text-[#10231e]">{field.label} {field.optional ? <span className="font-normal text-[#60706a]">(optional)</span> : null}</span>
      {field.type === 'textarea' ? (
        <textarea id={id} rows={4} value={value} onChange={(event) => onChange(event.target.value)} aria-invalid={Boolean(error)} aria-describedby={describedBy} className={inputClass(Boolean(error))} placeholder={field.placeholder} />
      ) : field.type === 'select' ? (
        <select id={id} value={value} onChange={(event) => onChange(event.target.value)} aria-invalid={Boolean(error)} aria-describedby={describedBy} className={inputClass(Boolean(error))}>
          <option value="">Select an option</option>
          {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      ) : (
        <input id={id} type={field.type ?? 'text'} value={value} onChange={(event) => onChange(event.target.value)} min={field.min} max={field.max} aria-invalid={Boolean(error)} aria-describedby={describedBy} className={inputClass(Boolean(error))} placeholder={field.placeholder} autoComplete={field.type === 'password' ? 'new-password' : undefined} />
      )}
      {error ? <span id={`${id}-error`} role="alert" className="text-xs font-semibold text-rose-600">{error}</span> : null}
    </label>
  );
}

export function RoleSignupForm({ config }: { config: SignupConfig }) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<Values>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptPrivacy, setAcceptPrivacy] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const reviewStep = config.steps.length;
  const isReview = step === reviewStep;
  const totalSteps = config.steps.length + 1;
  const currentFields = config.steps[step]?.fields ?? [];
  const allFields = useMemo(() => config.steps.flatMap((item) => item.fields), [config.steps]);

  function update(name: string, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: '' }));
  }

  function validateCurrent() {
    const nextErrors: Record<string, string> = {};
    for (const field of currentFields) {
      const error = validateField(field, values[field.name] ?? '');
      if (error) nextErrors[field.name] = error;
    }
    if (values.password && values.confirm_password && values.password !== values.confirm_password) nextErrors.confirm_password = 'Passwords do not match.';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function next() {
    if (!validateCurrent()) return;
    setStep((current) => Math.min(current + 1, reviewStep));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function submit() {
    if (!acceptTerms || !acceptPrivacy) {
      setServerError('Accept the terms of service and privacy notice before submitting.');
      return;
    }
    setSubmitting(true);
    setServerError('');
    const common: Record<string, unknown> = { accept_terms: acceptTerms, accept_privacy: acceptPrivacy, marketing_consent: marketingConsent, consent_version: '2026-07' };
    const data: Record<string, string> = {};
    for (const [key, value] of Object.entries(values)) {
      if (topLevelFields.has(key)) common[key] = value || undefined;
      else data[key] = value;
    }
    common.data = data;
    try {
      const response = await api.post(`/api/v1/signup/${config.role}`, common) as SignupResponse;
      router.push(`/signup/status?id=${encodeURIComponent(response.id)}&reference=${encodeURIComponent(response.reference)}&status=${encodeURIComponent(response.status)}`);
    } catch (caught) {
      setServerError(caught instanceof Error ? caught.message : 'Unable to submit this application.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link href="/signup" className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-[#0b5d4b]"><ArrowLeft className="h-4 w-4" />All workspaces</Link>
        <Link href={config.loginPath} className="text-sm font-bold text-[#0b5d4b]">Existing-user sign in</Link>
      </div>
      <div className="rounded-2xl border border-[#dbe2dc] bg-white p-4 sm:p-6">
        <div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-[#0b5d4b]" /><div><p className="font-bold text-[#10231e]">{config.access}</p><p className="mt-1 text-sm leading-6 text-[#60706a]">Submitting this form never bypasses verification or invitation controls.</p></div></div>
      </div>
      <ol className="mt-6 grid gap-2" style={{ gridTemplateColumns: `repeat(${totalSteps}, minmax(0, 1fr))` }} aria-label="Signup progress">
        {Array.from({ length: totalSteps }, (_, index) => <li key={index} className={`h-2 rounded-full ${index <= step ? 'bg-[#0b5d4b]' : 'bg-[#dbe2dc]'}`}><span className="sr-only">Step {index + 1}{index === step ? ', current' : ''}</span></li>)}
      </ol>
      <p className="mt-3 text-xs font-bold uppercase tracking-wider text-[#60706a]">Step {step + 1} of {totalSteps}</p>

      <section className="mt-5 rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] p-5 sm:p-8">
        {!isReview ? (
          <>
            <h2 className="text-2xl font-black text-[#10231e]">{config.steps[step].title}</h2>
            <p className="mt-2 text-sm leading-6 text-[#60706a]">{config.steps[step].description}</p>
            <div className="mt-7 grid gap-5 sm:grid-cols-2">
              {currentFields.map((field) => <FieldControl key={field.name} field={field} value={values[field.name] ?? ''} error={errors[field.name]} onChange={(value) => update(field.name, value)} />)}
            </div>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-black text-[#10231e]">Review and submit</h2>
            <p className="mt-2 text-sm leading-6 text-[#60706a]">Confirm the information below. Sensitive passwords are never displayed or stored in the browser.</p>
            <dl className="mt-7 grid gap-3 sm:grid-cols-2">
              {allFields.filter((field) => values[field.name] && field.type !== 'password').map((field) => <div key={field.name} className="rounded-xl border border-[#dbe2dc] bg-white p-4"><dt className="text-xs font-bold uppercase tracking-wider text-[#60706a]">{field.label}</dt><dd className="mt-1 break-words text-sm font-semibold text-[#10231e]">{values[field.name]}</dd></div>)}
            </dl>
            <div className="mt-7 grid gap-3">
              <label className="flex items-start gap-3 text-sm text-[#10231e]"><input type="checkbox" checked={acceptTerms} onChange={(event) => setAcceptTerms(event.target.checked)} className="mt-1 h-4 w-4 accent-[#0b5d4b]" /><span>I accept the <Link href="/terms" className="font-bold text-[#0b5d4b]">terms of service</Link>.</span></label>
              <label className="flex items-start gap-3 text-sm text-[#10231e]"><input type="checkbox" checked={acceptPrivacy} onChange={(event) => setAcceptPrivacy(event.target.checked)} className="mt-1 h-4 w-4 accent-[#0b5d4b]" /><span>I accept the <Link href="/privacy" className="font-bold text-[#0b5d4b]">privacy notice</Link> and consent to processing for onboarding.</span></label>
              <label className="flex items-start gap-3 text-sm text-[#60706a]"><input type="checkbox" checked={marketingConsent} onChange={(event) => setMarketingConsent(event.target.checked)} className="mt-1 h-4 w-4 accent-[#0b5d4b]" /><span>Send occasional product updates (optional).</span></label>
            </div>
          </>
        )}
        {serverError ? <p role="alert" className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{serverError}</p> : null}
        <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
          <button type="button" onClick={() => setStep((current) => Math.max(0, current - 1))} disabled={step === 0 || submitting} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-[#dbe2dc] bg-white px-6 text-sm font-bold text-[#10231e] disabled:opacity-40"><ArrowLeft className="h-4 w-4" />Previous</button>
          {isReview ? <button type="button" onClick={() => void submit()} disabled={submitting} className="sv-button-dark min-w-48">{submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}{submitting ? 'Submitting...' : 'Submit application'}</button> : <button type="button" onClick={next} className="sv-button-dark min-w-48">Save and continue <ArrowRight className="h-4 w-4" /></button>}
        </div>
      </section>
      <p className="mx-auto mt-5 max-w-2xl text-center text-xs leading-5 text-[#60706a]">Your information is used only for account creation, identity verification and regulatory review. Sensitive signup drafts are kept only in this page session and are not written to browser storage.</p>
    </div>
  );
}