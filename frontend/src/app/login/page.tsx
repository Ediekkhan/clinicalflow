'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Building2, LogIn, UserRound } from 'lucide-react';
import { api } from '@/lib/auth';
import { validators } from '@/lib/validators';

const demoPatientCredentials = {
  phone: '+234 803 456 7890',
  password: '@Klau2mari2',
};

const demoPatientUser = {
  id: 'demo-patient-adaeze',
  first_name: 'Adaeze',
  last_name: 'Chukwu',
  phone: demoPatientCredentials.phone,
  state: 'Akwa Ibom',
  lga: 'Uyo',
  health_card_id: 'SV-AKS-2026-00412',
  created_at: '2026-06-20T00:00:00.000Z',
};

function normalizePhone(value: string) {
  return value.replace(/\s+/g, '');
}

export default function PatientLoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const normalizedPhone = normalizePhone(phone);
    const phoneError = validators.phone(normalizedPhone);
    const passwordError = validators.password(password);
    if (phoneError || passwordError) {
      setError(phoneError ?? passwordError ?? 'Invalid login details');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/v1/auth/patient/login', { phone: normalizedPhone, password });
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem('synaptiverse_demo_patient');
      }
      router.push('/dashboard');
    } catch (caught) {
      if (normalizedPhone === normalizePhone(demoPatientCredentials.phone) && password === demoPatientCredentials.password) {
        if (typeof window !== 'undefined') {
          window.localStorage.setItem('synaptiverse_demo_patient', JSON.stringify(demoPatientUser));
          window.localStorage.setItem('sv_user_type', 'PATIENT');
        }
        router.push('/dashboard');
        return;
      }
      setError(caught instanceof Error ? caught.message : 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#0D1117] p-4">
      <form onSubmit={submit} className="grid w-full max-w-md gap-5 rounded-2xl border border-white/10 bg-white p-6 shadow-xl">
        <div className="text-center">
          <p className="font-display text-4xl text-[#2563EB]">SynaptiVerse</p>
          <h1 className="mt-3 text-xl font-bold text-slate-900">Patient Login</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">Sign in to view your health card, AI triage chat, and live queue status.</p>
        </div>
        <label className="grid gap-2 text-sm font-bold text-slate-900">
          Phone number
          <input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder={demoPatientCredentials.phone} className="min-h-12 rounded-lg border border-slate-200 px-4 py-2.5 outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100" />
        </label>
        <label className="grid gap-2 text-sm font-bold text-slate-900">
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="min-h-12 rounded-lg border border-slate-200 px-4 py-2.5 outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100" />
        </label>
        {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-600">{error}</p> : null}
        <button disabled={loading} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1D4ED8] disabled:bg-slate-300">
          <LogIn className="h-5 w-5" />
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
        <div className="grid gap-3 border-t border-slate-100 pt-4">
          <Link href="/signup" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-blue-50 px-4 py-2.5 text-sm font-semibold text-[#2563EB]">
            <UserRound className="h-4 w-4" />
            Create patient account
          </Link>
          <Link href="/specialist/login" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700">
            <Building2 className="h-4 w-4" />
            Doctor / staff login
          </Link>
        </div>
      </form>
    </main>
  );
}
