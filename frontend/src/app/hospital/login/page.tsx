'use client';

import { Building2, LogIn, Stethoscope, UserCog } from 'lucide-react';
import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/auth';
import { AuthFrame } from '@/components/auth/AuthFrame';

const roles = [
  { label: 'Doctor / Specialist', value: 'doctor', icon: Stethoscope },
  { label: 'Nurse / Front Desk', value: 'nurse', icon: Building2 },
  { label: 'Hospital Admin', value: 'hospital_admin', icon: UserCog },
] as const;

export default function HospitalLoginPage() {
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
      const session = await api.post('/api/v1/auth/hospital/account-login', { hospital_code: hospitalCode, role, password });
      if (typeof document !== 'undefined') {
        const secure = window.location.protocol === 'https:' ? '; Secure' : '';
        const sessionRole = typeof session === 'object' && session && 'role' in session ? String(session.role) : role;
        document.cookie = `synaptiverse_role=${encodeURIComponent(sessionRole)}; Max-Age=1209600; Path=/; SameSite=Lax${secure}`;
      }
      window.location.assign('/hospital/dashboard');
    } catch (caught) {
      setServerError(caught instanceof Error ? caught.message : 'Invalid hospital credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthFrame eyebrow="Facility access" title="Enter your hospital workspace." description="Doctors, nurses, and administrators see only the patients, queues, and controls relevant to their role.">
      <form onSubmit={submit} className="grid max-w-lg gap-5">
        <div className="grid gap-2">
          {roles.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setRole(item.value)}
              className={cn(
                'front-desk-target flex items-center justify-center gap-2 border',
                role === item.value
                  ? 'border-[#0b5d4b] bg-[#e9f6f1] text-[#0b5d4b]'
                  : 'border-[#dbe2dc] bg-white text-[#60706a]',
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </button>
          ))}
        </div>
        <label className="grid gap-2 text-sm font-bold text-[#10231e]">
          Hospital code
          <input
            value={hospitalCode}
            onChange={(event) => setHospitalCode(event.target.value)}
            className="min-h-14 rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] px-5 outline-none focus:border-[#0b5d4b]"
          />
          {errors.hospitalCode ? <span className="text-xs text-[#DC2626]">{errors.hospitalCode}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#10231e]">
          Hospital password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password123!"
            className="min-h-14 rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] px-5 outline-none focus:border-[#0b5d4b]"
          />
          {errors.password ? <span className="text-xs text-[#DC2626]">{errors.password}</span> : null}
        </label>
        {serverError ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-600">{serverError}</p> : null}
        <button
          type="submit"
          disabled={!valid || loading}
          className="sv-button-dark w-full"
        >
          <LogIn className="h-5 w-5" />
          {loading ? 'Signing in…' : 'Enter Hospital Workspace'}
        </button>
      </form>
    </AuthFrame>
  );
}
