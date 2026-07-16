'use client';

import { Building2, LogIn, Stethoscope, UserCog } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { api } from '@/lib/auth';

const roles = [
  { label: 'Doctor / Specialist', value: 'doctor', icon: Stethoscope },
  { label: 'Nurse / Front Desk', value: 'nurse', icon: Building2 },
  { label: 'Hospital Admin', value: 'hospital_admin', icon: UserCog },
] as const;

export default function HospitalLoginPage() {
  const router = useRouter();
  const [role, setRole] = useState<(typeof roles)[number]['value']>('doctor');
  const [hospitalCode, setHospitalCode] = useState('UYO-FAMILY');
  const [password, setPassword] = useState('');
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);
  const errors = useMemo(
    () => ({
      hospitalCode: hospitalCode.trim().length < 3 ? 'Enter the hospital account code.' : '',
      password: password.length >= 4 ? '' : 'Enter the hospital account password.',
    }),
    [hospitalCode, password],
  );
  const valid = !errors.hospitalCode && !errors.password;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!valid) return;
    setLoading(true);
    setServerError('');
    try {
      await api.post('/api/v1/auth/hospital/account-login', { hospital_code: hospitalCode, role, password });
      router.push(role === 'doctor' ? '/hospital/doctor/patients' : '/hospital/dashboard');
    } catch (caught) {
      setServerError(caught instanceof Error ? caught.message : 'Invalid hospital credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#0D1117] p-4">
      <form onSubmit={submit} className="grid w-full max-w-md gap-5 rounded-card border border-white/10 bg-white p-5 shadow-md md:p-6">
        <div className="text-center">
          <p className="font-display text-4xl text-[#2563EB]">SynaptiVerse</p>
          <h1 className="mt-3 text-xl font-bold text-[#111827]">Hospital Account Login</h1>
          <p className="mt-2 text-sm leading-6 text-[#6B7280]">
            Doctors, nurses, and admins sign into the hospital account, then see only the queues and patients relevant to their role.
          </p>
        </div>
        <div className="grid gap-2">
          {roles.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setRole(item.value)}
              className={cn(
                'front-desk-target flex items-center justify-center gap-2 border',
                role === item.value
                  ? 'border-[#2563EB] bg-[#e0f2fe] text-[#2563EB]'
                  : 'border-[#E5E7EB] bg-white text-[#6B7280]',
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </button>
          ))}
        </div>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Hospital code
          <input
            value={hospitalCode}
            onChange={(event) => setHospitalCode(event.target.value)}
            className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#2563EB]"
          />
          {errors.hospitalCode ? <span className="text-xs text-[#DC2626]">{errors.hospitalCode}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Hospital password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password123!"
            className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#2563EB]"
          />
          {errors.password ? <span className="text-xs text-[#DC2626]">{errors.password}</span> : null}
        </label>
        {serverError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-600">{serverError}</p> : null}
        <button
          type="submit"
          disabled={!valid || loading}
          className="front-desk-target inline-flex items-center justify-center gap-2 bg-[#2563EB] text-white hover:bg-blue-700"
        >
          <LogIn className="h-5 w-5" />
          {loading ? 'Signing in…' : 'Enter Hospital Workspace'}
        </button>
      </form>
    </main>
  );
}
