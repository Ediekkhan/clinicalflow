'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowRight, Building2, Eye, EyeOff, LogIn, UserRound } from 'lucide-react';
import { AuthFrame } from '@/components/auth/AuthFrame';
import { api } from '@/lib/auth';
import { validators } from '@/lib/validators';

function normalizePhone(value: string) {
  return value.replace(/\s+/g, '');
}

export default function PatientLoginPage() {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

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
      const session = await api.post('/api/v1/auth/patient/login', { phone: normalizedPhone, password });
      window.location.assign('/dashboard');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthFrame eyebrow="Patient access" title="Welcome back. Let’s continue your care." description="Your AI symptom check, appointments, health card, and live queue are together in one secure place.">
      <form onSubmit={submit} className="grid max-w-lg gap-5">
        <label className="grid gap-2 text-sm font-bold text-[#10231e]">
          Phone number
          <input aria-label="Phone number" autoComplete="tel" type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="e.g. +234 800 000 0000" className="min-h-14 rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] px-5 outline-none focus:border-[#0b5d4b]" />
        </label>
        <label className="grid gap-2 text-sm font-bold text-[#10231e]">
          Password
          <span className="relative"><input aria-label="Password" autoComplete="current-password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} className="min-h-14 w-full rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] px-5 pr-14 outline-none focus:border-[#0b5d4b]" /><button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-2 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-full text-[#60706a]" aria-label={showPassword ? 'Conceal credentials' : 'Reveal credentials'}>{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></span>
        </label>
        {error ? <p role="alert" className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p> : null}
        <button disabled={loading} className="sv-button-dark w-full">
          <LogIn className="h-5 w-5" />
          {loading ? 'Signing in...' : 'Sign In'}
          {!loading ? <ArrowRight className="h-4 w-4" /> : null}
        </button>
        <div className="grid gap-3 border-t border-[#dbe2dc] pt-5 sm:grid-cols-2">
          <Link href="/signup?type=patient" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#e9f6f1] px-4 py-2.5 text-sm font-bold text-[#0b5d4b]">
            <UserRound className="h-4 w-4" />
            Patient account options
          </Link>
          <Link href="/signup" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-[#dbe2dc] bg-white px-4 py-2.5 text-sm font-bold text-[#10231e]">
            <Building2 className="h-4 w-4" />
            All workspaces
          </Link>
        </div>
      </form>
    </AuthFrame>
  );
}
