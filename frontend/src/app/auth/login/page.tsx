'use client';

import { useMemo, useState } from 'react';
import { ShieldCheck, Stethoscope } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { api } from '@/lib/auth';

const roles = [
  { label: 'Clinic Nurse', value: 'NURSE', icon: Stethoscope },
  { label: 'System Administrator', value: 'ADMIN', icon: ShieldCheck },
] as const;

export default function LoginPage() {
  const router = useRouter();
  const [role, setRole] = useState<(typeof roles)[number]['value']>('NURSE');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const masked = useMemo(() => Array.from({ length: 4 }, (_, index) => (pin[index] ? '●' : '○')).join(' '), [pin]);

  function press(value: string) {
    if (value === 'clear') {
      setPin('');
      return;
    }
    setPin((current) => (current.length < 4 ? current + value : current));
  }

  async function login() {
    if (pin.length !== 4 || loading) return;
    setLoading(true);
    setError('');
    try {
      await api.post('/api/v1/auth/staff/pin-login', { role: role.toLowerCase(), pin });
      router.push(role === 'ADMIN' ? '/dashboard/admin' : '/nurse/queue');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Invalid role or PIN');
      setPin('');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-4 md:p-6">
      <section className="grid w-full max-w-xl gap-6 rounded-lg border border-slate-800 bg-slate-900 p-4 text-white shadow-2xl md:p-6">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-blue-300">Secure Gateway</p>
          <h1 className="text-2xl font-bold tracking-tight">[PROJECT_NAME]</h1>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {roles.map((item) => (
            <button
              key={item.value}
              onClick={() => setRole(item.value)}
              className={cn(
                'front-desk-target flex items-center justify-center gap-2 border',
                role === item.value
                  ? 'border-blue-500 bg-blue-600 text-white'
                  : 'border-slate-700 bg-slate-950 text-slate-300 hover:bg-slate-800',
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </button>
          ))}
        </div>
        <div className="rounded-lg bg-slate-950 p-4 text-center font-mono text-2xl font-bold tracking-tight">
          {masked}
        </div>
        {error ? <p className="rounded-lg bg-rose-950 px-4 py-3 text-sm font-semibold text-rose-200">{error}</p> : null}
        <div className="grid grid-cols-3 gap-3">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'clear', '0', 'login'].map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => (key === 'login' ? void login() : press(key))}
              disabled={loading || (key === 'login' && pin.length !== 4)}
              className={cn(
                'front-desk-target bg-slate-800 text-white hover:bg-slate-700',
                key === 'login' && 'bg-blue-600 hover:bg-blue-700',
                key === 'clear' && 'bg-slate-700',
              )}
            >
              {key === 'login' ? (loading ? 'Wait…' : 'Login') : key === 'clear' ? 'Clear' : key}
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
