'use client';

import { CheckCircle2, LocateFixed, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import { PatientCard } from '@/components/PatientCard';
import { useGeolocation } from '@/hooks/useGeolocation';
import { demoPatient } from '@/lib/syn-data';
import { cn } from '@/lib/utils';
import type { Gender } from '@/types';

const genders: Gender[] = ['MALE', 'FEMALE', 'OTHER'];

export default function SignupPage() {
  const { coords, error: locationError, requestLocation } = useGeolocation();
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({
    fullName: '',
    phone: '+234',
    dob: '',
    gender: 'MALE' as Gender,
    password: '',
    confirm: '',
    town: '',
  });

  const errors = useMemo(() => ({
    fullName: form.fullName.trim().length < 3 ? 'Enter the patient full name.' : '',
    phone: form.phone.length < 8 ? 'Enter a valid Nigerian phone number.' : '',
    dob: !form.dob ? 'Date of birth is required.' : '',
    password: form.password.length < 8 ? 'Use at least 8 characters.' : '',
    confirm: form.password !== form.confirm ? 'Passwords must match.' : '',
    location: !coords && !form.town.trim() ? 'Allow location or enter your LGA / nearest town.' : '',
  }), [coords, form]);

  const hasErrors = Object.values(errors).some(Boolean);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (hasErrors) return;
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#F7F8FA] p-4 md:p-6">
        <section className="w-full max-w-xl">
          <div className="mb-6 text-center">
            <CheckCircle2 className="mx-auto h-10 w-10 text-[#0D7A5F]" />
            <h1 className="font-display mt-3 text-4xl text-[#111827]">Your SynaptiVerse card is ready</h1>
          </div>
          <PatientCard patient={{ ...demoPatient, full_name: form.fullName || demoPatient.full_name, phone: form.phone, date_of_birth: form.dob || demoPatient.date_of_birth, gender: form.gender }} reveal />
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#F7F8FA] p-4 md:p-6">
      <form onSubmit={submit} className="mx-auto grid max-w-[480px] gap-5 rounded-card border border-[#E5E7EB] bg-white p-5 shadow-sm md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Patient Signup</p>
          <h1 className="font-display text-4xl text-[#111827]">Join SynaptiVerse</h1>
        </div>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Full Name
          <input value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]" />
          {errors.fullName ? <span className="text-xs text-[#DC2626]">{errors.fullName}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Phone Number
          <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]" />
          {errors.phone ? <span className="text-xs text-[#DC2626]">{errors.phone}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Date of Birth
          <input type="date" value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]" />
          {errors.dob ? <span className="text-xs text-[#DC2626]">{errors.dob}</span> : null}
        </label>
        <fieldset className="grid gap-2">
          <legend className="text-sm font-bold text-[#111827]">Gender</legend>
          <div className="grid grid-cols-3 gap-2">
            {genders.map((gender) => (
              <button type="button" key={gender} onClick={() => setForm({ ...form, gender })} className={cn('min-h-12 rounded-lg border px-3 text-sm font-bold', form.gender === gender ? 'border-[#0D7A5F] bg-[#E6F4F0] text-[#0D7A5F]' : 'border-[#E5E7EB] text-[#6B7280]')}>
                {gender}
              </button>
            ))}
          </div>
        </fieldset>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Password
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]" />
          {errors.password ? <span className="text-xs text-[#DC2626]">{errors.password}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Confirm Password
          <input type="password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]" />
          {errors.confirm ? <span className="text-xs text-[#DC2626]">{errors.confirm}</span> : null}
        </label>
        <section className="rounded-card border border-[#E5E7EB] bg-[#F7F8FA] p-4">
          <div className="flex gap-3">
            <LocateFixed className="h-6 w-6 text-[#0D7A5F]" />
            <div>
              <h2 className="text-sm font-bold text-[#111827]">Allow SynaptiVerse to detect your location for nearby clinic matching</h2>
              <button type="button" onClick={requestLocation} className="touch-target mt-3 bg-[#0D7A5F] text-white hover:bg-emerald-700">Allow Location</button>
            </div>
          </div>
          {coords ? <p className="mt-3 text-sm text-[#0D7A5F]">Location captured securely.</p> : null}
          {locationError ? (
            <label className="mt-3 grid gap-2 text-sm font-bold text-[#111827]">
              Enter your LGA or nearest town
              <input value={form.town} onChange={(e) => setForm({ ...form, town: e.target.value })} className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]" />
            </label>
          ) : null}
          {errors.location ? <span className="mt-2 block text-xs text-[#DC2626]">{errors.location}</span> : null}
        </section>
        <button type="submit" className="front-desk-target inline-flex items-center justify-center gap-2 bg-[#0D7A5F] text-white hover:bg-emerald-700">
          <ShieldCheck className="h-5 w-5" />
          Create Health Identity
        </button>
      </form>
    </main>
  );
}

