'use client';

import Link from 'next/link';
import { Building2, LogIn, Stethoscope, UserCog } from 'lucide-react';
import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

const roles = [
  { label: 'Doctor / Specialist', value: 'DOCTOR', icon: Stethoscope },
  { label: 'Nurse / Front Desk', value: 'NURSE', icon: Building2 },
  { label: 'Hospital Admin', value: 'ADMIN', icon: UserCog },
] as const;

const hospitalPassword = 'klau2mari2';

export default function HospitalLoginPage() {
  const [role, setRole] = useState<(typeof roles)[number]['value']>('DOCTOR');
  const [hospitalCode, setHospitalCode] = useState('UYO-FAMILY');
  const [password, setPassword] = useState('');
  const errors = useMemo(
    () => ({
      hospitalCode: hospitalCode.trim().length < 3 ? 'Enter the hospital account code.' : '',
      password: password === hospitalPassword ? '' : 'Enter the correct hospital account password.',
    }),
    [hospitalCode, password],
  );
  const valid = !errors.hospitalCode && !errors.password;

  return (
    <main className="grid min-h-screen place-items-center bg-[#0D1117] p-4">
      <form className="grid w-full max-w-md gap-5 rounded-card border border-white/10 bg-white p-5 shadow-md md:p-6">
        <div className="text-center">
          <p className="font-display text-4xl text-[#0D7A5F]">SynaptiVerse</p>
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
                  ? 'border-[#0D7A5F] bg-[#E6F4F0] text-[#0D7A5F]'
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
            className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]"
          />
          {errors.hospitalCode ? <span className="text-xs text-[#DC2626]">{errors.hospitalCode}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Hospital password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="klau2mari2"
            className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]"
          />
          {errors.password ? <span className="text-xs text-[#DC2626]">{errors.password}</span> : null}
        </label>
        <Link
          href={valid ? (role === 'DOCTOR' ? '/hospital/doctor/patients' : '/hospital/dashboard') : '#'}
          className="front-desk-target inline-flex items-center justify-center gap-2 bg-[#0D7A5F] text-white hover:bg-emerald-700"
        >
          <LogIn className="h-5 w-5" />
          Enter Hospital Workspace
        </Link>
      </form>
    </main>
  );
}
