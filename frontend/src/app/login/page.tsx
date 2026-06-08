'use client';

import Link from 'next/link';
import { ArrowRight, Building2, LogIn, UserRound } from 'lucide-react';
import { useMemo, useState } from 'react';

export default function PatientLoginPage() {
  const [phone, setPhone] = useState('+234');
  const [password, setPassword] = useState('');

  const errors = useMemo(
    () => ({
      phone: phone.length < 8 ? 'Enter your registered phone number.' : '',
      password: password.length < 8 ? 'Enter your password.' : '',
    }),
    [phone, password],
  );

  const valid = !errors.phone && !errors.password;

  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F8FA] p-4">
      <section className="grid w-full max-w-md gap-5 rounded-card border border-[#E5E7EB] bg-white p-5 shadow-sm md:p-6">
        <div className="text-center">
          <p className="font-display text-4xl text-[#0D7A5F]">SynaptiVerse</p>
          <h1 className="mt-3 text-xl font-bold text-[#111827]">Patient Login</h1>
          <p className="mt-2 text-sm leading-6 text-[#6B7280]">
            Sign in to view your health card, appointments, AI triage chat, and live queue status.
          </p>
        </div>

        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Phone number
          <input
            type="tel"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]"
          />
          {errors.phone ? <span className="text-xs text-[#DC2626]">{errors.phone}</span> : null}
        </label>

        <label className="grid gap-2 text-sm font-bold text-[#111827]">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="min-h-12 rounded-lg border border-[#E5E7EB] px-4 py-2.5 outline-none focus:border-[#0D7A5F]"
          />
          {errors.password ? <span className="text-xs text-[#DC2626]">{errors.password}</span> : null}
        </label>

        <Link
          href={valid ? '/dashboard' : '#'}
          className="front-desk-target inline-flex items-center justify-center gap-2 bg-[#0D7A5F] text-white hover:bg-emerald-700"
        >
          <LogIn className="h-5 w-5" />
          Sign In
        </Link>

        <div className="grid gap-3 border-t border-[#E5E7EB] pt-4">
          <Link
            href="/signup"
            className="touch-target inline-flex items-center justify-center gap-2 bg-[#E6F4F0] text-[#0D7A5F] hover:bg-emerald-100"
          >
            <UserRound className="h-4 w-4" />
            Create patient account
          </Link>
          <Link
            href="/hospital/login"
            className="touch-target inline-flex items-center justify-center gap-2 border border-[#E5E7EB] bg-white text-[#111827] hover:bg-[#F7F8FA]"
          >
            <Building2 className="h-4 w-4" />
            Hospital staff login
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}

