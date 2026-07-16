'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { LogIn, Stethoscope } from 'lucide-react';
import { api } from '@/lib/auth';
import { validators } from '@/lib/validators';
import { AuthFrame } from '@/components/auth/AuthFrame';

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
    <AuthFrame eyebrow="Clinical team access" title="Welcome back, specialist." description="Open your patient queue, consultation notes, clinical schedule, and secure messages.">
      <form onSubmit={submit} className="grid max-w-lg gap-5">
        <div className="grid h-12 w-12 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><Stethoscope className="h-6 w-6" /></div>
        <label className="grid gap-2 text-sm font-bold text-slate-900">
          Email address
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="min-h-14 rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] px-5 outline-none focus:border-[#0b5d4b]" />
        </label>
        <label className="grid gap-2 text-sm font-bold text-slate-900">
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="min-h-14 rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] px-5 outline-none focus:border-[#0b5d4b]" />
        </label>
        {error ? <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-600">{error}</p> : null}
        <button disabled={loading} className="sv-button-dark w-full">
          <LogIn className="h-5 w-5" />
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
        <Link href="/signup?type=specialist" className="text-center text-sm font-bold text-[#0b5d4b]">Explore the specialist demo</Link>
      </form>
    </AuthFrame>
  );
}
