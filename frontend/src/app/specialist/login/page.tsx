'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { LogIn, Stethoscope } from 'lucide-react';
import { api } from '@/lib/auth';
import { validators } from '@/lib/validators';

export default function SpecialistLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const passwordError = validators.password(password);
    if (!email.includes('@') || passwordError) {
      setError(passwordError ?? 'Enter a valid email address');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/v1/auth/specialist/login', { email, password });
      router.push('/specialist/dashboard');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#0D1117] p-4">
      <form onSubmit={submit} className="grid w-full max-w-md gap-5 rounded-2xl border border-white/10 bg-white p-6 shadow-xl">
        <div className="text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-blue-50 text-[#2563EB]"><Stethoscope className="h-6 w-6" /></div>
          <h1 className="font-display mt-4 text-4xl text-slate-900">Specialist Login</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">Access your SynaptiVerse patient queue, notes, schedule, and earnings.</p>
        </div>
        <label className="grid gap-2 text-sm font-bold text-slate-900">
          Email address
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="min-h-12 rounded-lg border border-slate-200 px-4 py-2.5 outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100" />
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
        <Link href="/signup?type=specialist" className="text-center text-sm font-semibold text-[#2563EB]">Register as a specialist</Link>
      </form>
    </main>
  );
}
