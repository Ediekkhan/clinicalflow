'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Check, Loader2, MapPin, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/auth';
import { useGeolocation } from '@/hooks/useGeolocation';
import type { SignupConfig, SignupField } from '@/lib/signup-config';

type Values = Record<string, string>;
type SignupResponse = { id: string; reference: string; status: string };
type LookupOption = { id: string; name: string; location?: string };
type InvitationContext = { hospital_name?: string; department_id: string; intended_role: string; specialty_id?: string; employment_type?: string };

const countryData: Record<string, { code: string; states: string[] }> = {
  Nigeria: { code: '+234', states: ['Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara', 'Federal Capital Territory'] },
  Ghana: { code: '+233', states: ['Ashanti', 'Bono', 'Central', 'Eastern', 'Greater Accra', 'Northern', 'Upper East', 'Upper West', 'Volta', 'Western'] },
  Kenya: { code: '+254', states: ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Kiambu', 'Machakos', 'Uasin Gishu', 'Kakamega'] },
  'South Africa': { code: '+27', states: ['Eastern Cape', 'Free State', 'Gauteng', 'KwaZulu-Natal', 'Limpopo', 'Mpumalanga', 'Northern Cape', 'North West', 'Western Cape'] },
  'United Kingdom': { code: '+44', states: ['England', 'Scotland', 'Wales', 'Northern Ireland'] },
  'United States': { code: '+1', states: ['Alabama', 'California', 'Florida', 'Georgia', 'Illinois', 'New York', 'Texas', 'Washington'] },
};

const countryDialingCodes = Object.values(countryData).map(({ code }) => code).sort((left, right) => right.length - left.length);

const topLevelFields = new Set(['first_name', 'middle_name', 'last_name', 'full_name', 'phone', 'email', 'country', 'region', 'password', 'confirm_password', 'invitation_token']);
const coordinateFields = new Set(['latitude', 'longitude']);

function inputClass(hasError: boolean) {
  return `min-h-12 w-full rounded-xl border bg-white px-4 py-3 text-sm text-[#10231e] outline-none transition ${hasError ? 'border-rose-400 focus:ring-2 focus:ring-rose-100' : 'border-[#dbe2dc] focus:border-[#0b5d4b] focus:ring-2 focus:ring-[#e9f6f1]'}`;
}

function autoCompleteFor(fieldName: string) {
  const values: Record<string, string> = {
    first_name: 'given-name', last_name: 'family-name', full_name: 'name',
    email: 'email', phone: 'tel', administrator_phone: 'tel', official_phone: 'tel',
    administrator_name: 'name', address: 'street-address', head_office_address: 'street-address',
    country: 'country-name', region: 'address-level1', city: 'address-level2',
    password: 'new-password', confirm_password: 'new-password',
  };
  return values[fieldName];
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

function FieldControl({ field, value, error, onChange, lookupOptions, options }: { field: SignupField; value: string; error?: string; onChange: (value: string) => void; lookupOptions?: LookupOption[]; options?: string[] }) {
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
          {lookupOptions ? lookupOptions.map((option) => <option key={option.id} value={option.id}>{option.name}{option.location ? ` - ${option.location}` : ''}</option>) : (options ?? field.options)?.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      ) : (
        <input id={id} type={field.type ?? 'text'} value={value} onChange={(event) => onChange(event.target.value)} min={field.min} max={field.max} aria-invalid={Boolean(error)} aria-describedby={describedBy} className={inputClass(Boolean(error))} placeholder={field.placeholder} autoComplete={autoCompleteFor(field.name) ?? (field.type === 'password' ? 'new-password' : undefined)} />
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
  const [staffMethod, setStaffMethod] = useState<'INVITATION' | 'JOIN_REQUEST'>('INVITATION');
  const [hospitals, setHospitals] = useState<LookupOption[]>([]);
  const [departments, setDepartments] = useState<LookupOption[]>([]);
  const [invitationContext, setInvitationContext] = useState<InvitationContext | null>(null);
  const { coords, error: locationError, isLoading: locationLoading, requestLocation } = useGeolocation();
  const reviewStep = config.steps.length;
  const isReview = step === reviewStep;
  const totalSteps = config.steps.length + 1;
  const rawCurrentFields = config.steps[step]?.fields ?? [];
  const isHospitalStaff = config.role === 'specialist' || config.role === 'nurse';
  const isMembershipStep = isHospitalStaff && config.steps[step]?.title === 'Hospital membership';
  const invitationFields = new Set(['invitation_token']);
  const requestFields = new Set(['registered_hospital_id', 'department_id', 'staff_role']);
  const currentFields = isMembershipStep
    ? rawCurrentFields.filter((field) => staffMethod === 'INVITATION' ? !requestFields.has(field.name) && (invitationFields.has(field.name) || !['employment_type', 'employee_number', 'work_start_date'].includes(field.name)) : !invitationFields.has(field.name))
    : rawCurrentFields;
  const isFacilityLocationStep = ['hospital', 'clinic', 'pharmacy', 'laboratory'].includes(config.role) && config.steps[step]?.title.toLowerCase().includes('location');
  const allFields = useMemo(() => config.steps.flatMap((item) => item.fields), [config.steps]);

  useEffect(() => {
    if (!isHospitalStaff) return;
    const invite = new URLSearchParams(window.location.search).get('invite');
    if (invite) setValues((current) => ({ ...current, invitation_token: invite }));
  }, [isHospitalStaff]);

  useEffect(() => {
    if (!isHospitalStaff || staffMethod !== 'JOIN_REQUEST') return;
    void api.get('/api/v1/signup/registered-hospitals').then((response) => {
      const items = (response as { items?: LookupOption[] }).items;
      setHospitals(Array.isArray(items) ? items : []);
    }).catch(() => setServerError('Unable to load registered hospitals.'));
  }, [isHospitalStaff, staffMethod]);

  useEffect(() => {
    const hospitalId = values.registered_hospital_id;
    if (!hospitalId || staffMethod !== 'JOIN_REQUEST') { setDepartments([]); return; }
    void api.get(`/api/v1/signup/registered-hospitals/${hospitalId}/departments`).then((response) => {
      const items = (response as { items?: LookupOption[] }).items;
      setDepartments(Array.isArray(items) ? items : []);
    }).catch(() => setServerError('Unable to load hospital departments.'));
  }, [staffMethod, values.registered_hospital_id]);

  useEffect(() => {
    if (!coords || !isFacilityLocationStep) return;
    update('latitude', String(coords.latitude));
    update('longitude', String(coords.longitude));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coords, isFacilityLocationStep]);

  function update(name: string, value: string) {
    if (name === 'country') {
      const nextCountry = countryData[value];
      setValues((current) => {
        const currentPhone = (current.phone ?? '').trim();
        let phone = nextCountry?.code ?? '';
        const existingCode = countryDialingCodes.find((code) => currentPhone.startsWith(code));
        if (currentPhone && existingCode) {
          phone = `${nextCountry?.code ?? ''}${currentPhone.slice(existingCode.length)}`;
        } else if (currentPhone && current.country === value) {
          phone = currentPhone;
        }
        return { ...current, country: value, region: '', phone };
      });
    } else {
      setValues((current) => ({ ...current, [name]: value }));
    }
    if (name === 'invitation_token') setInvitationContext(null);
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

  async function next() {
    if (isFacilityLocationStep && (!values.latitude || !values.longitude)) {
      setServerError('Allow location access so we can capture the facility coordinates, then tap Next again.');
      requestLocation();
      return;
    }
    if (!validateCurrent()) return;
    if (isMembershipStep && staffMethod === 'INVITATION' && !invitationContext) {
      setServerError('');
      try {
        const context = await api.post('/api/v1/signup/invitations/validate', { token: values.invitation_token, role: config.role, email: values.email }) as InvitationContext & { valid: boolean };
        setInvitationContext(context);
        return;
      } catch (caught) {
        setInvitationContext(null);
        setServerError(caught instanceof Error ? caught.message : 'Unable to validate this invitation.');
        return;
      }
    }
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
    if (isHospitalStaff) data.onboarding_method = staffMethod;
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
            {isMembershipStep ? (
              <div className="mb-6 grid gap-3 sm:grid-cols-2" role="group" aria-label="Hospital membership method">
                <button type="button" onClick={() => { setStaffMethod('INVITATION'); setInvitationContext(null); setServerError(''); setValues((current) => ({ ...current, registered_hospital_id: '', department_id: '', staff_role: '' })); }} className={`min-h-14 rounded-xl border px-4 text-sm font-bold transition ${staffMethod === 'INVITATION' ? 'border-[#0b5d4b] bg-[#e9f6f1] text-[#0b5d4b]' : 'border-[#dbe2dc] bg-white text-[#60706a]'}`}>Accept hospital invitation</button>
                <button type="button" onClick={() => { setStaffMethod('JOIN_REQUEST'); setInvitationContext(null); setServerError(''); setValues((current) => ({ ...current, invitation_token: '' })); }} className={`min-h-14 rounded-xl border px-4 text-sm font-bold transition ${staffMethod === 'JOIN_REQUEST' ? 'border-[#0b5d4b] bg-[#e9f6f1] text-[#0b5d4b]' : 'border-[#dbe2dc] bg-white text-[#60706a]'}`}>Request to join an existing hospital</button>
              </div>
            ) : null}
            <h2 className="text-2xl font-black text-[#10231e]">{config.steps[step].title}</h2>
            <p className="mt-2 text-sm leading-6 text-[#60706a]">{config.steps[step].description}</p>
            <div className="mt-7 grid gap-5 sm:grid-cols-2">
              {currentFields.filter((field) => !coordinateFields.has(field.name)).map((field) => <FieldControl key={field.name} field={field} value={values[field.name] ?? ''} error={errors[field.name]} onChange={(value) => { update(field.name, value); if (field.name === 'registered_hospital_id') update('department_id', ''); }} options={field.name === 'region' ? (countryData[values.country]?.states ?? ['Select a country first']) : undefined} lookupOptions={field.name === 'registered_hospital_id' ? hospitals : field.name === 'department_id' ? departments : undefined} />)}
            </div>
            {isFacilityLocationStep ? <div className="mt-5 rounded-xl border border-[#dbe2dc] bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2"><MapPin className="h-5 w-5 text-[#0b5d4b]" /><div><p className="text-sm font-bold text-[#10231e]">Facility location</p><p className="text-xs text-[#60706a]">Use device location to set routing coordinates automatically.</p></div></div>
                <button type="button" onClick={() => requestLocation()} disabled={locationLoading} className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[#0b5d4b] px-4 text-sm font-bold text-[#0b5d4b] disabled:opacity-50">{locationLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPin className="h-4 w-4" />}{locationLoading ? 'Getting location...' : coords ? 'Refresh location' : 'Use my location'}</button>
              </div>
              {coords ? <p className="mt-3 text-xs font-semibold text-emerald-700">Location added. Coordinates will be used for nearest-facility routing.</p> : <p className="mt-3 text-xs text-[#60706a]">Location permission is required so patients can be routed accurately. Latitude and longitude will not be typed manually.</p>}
              {locationError ? <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">{locationError}</p> : null}
            </div> : null}
            {isMembershipStep && staffMethod === 'JOIN_REQUEST' ? <p className="mt-5 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">Your personal account will be created, but hospital access remains disabled until the hospital approves this membership.</p> : null}
            {isMembershipStep && invitationContext ? <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"><p className="font-bold">Invitation verified</p><p className="mt-1">{invitationContext.hospital_name} · {invitationContext.department_id} · {invitationContext.intended_role}{invitationContext.specialty_id ? ` · ${invitationContext.specialty_id}` : ''}</p><p className="mt-1 text-xs">Hospital, department, role and specialty are protected by the invitation.</p></div> : null}
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
          {isReview ? <button type="button" onClick={() => void submit()} disabled={submitting} className="sv-button-dark min-w-48">{submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}{submitting ? 'Submitting...' : 'Submit application'}</button> : <button type="button" onClick={() => void next()} disabled={locationLoading} className="sv-button-dark min-w-48">{isFacilityLocationStep && !values.latitude ? 'Use location and continue' : 'Save and continue'} <ArrowRight className="h-4 w-4" /></button>}
        </div>
      </section>
      <p className="mx-auto mt-5 max-w-2xl text-center text-xs leading-5 text-[#60706a]">Your information is used only for account creation, identity verification and regulatory review. Sensitive signup drafts are kept only in this page session and are not written to browser storage.</p>
    </div>
  );
}
