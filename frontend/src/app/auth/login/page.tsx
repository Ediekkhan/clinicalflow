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
    <main className="grid min-h-screen place-items-center bg-[#073d33] p-4 md:p-6">
      <section className="grid w-full max-w-xl gap-6 rounded-[2rem] border border-white/10 bg-white/10 p-5 text-white shadow-2xl backdrop-blur md:p-7">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-[#d8ee72]">Secure staff gateway</p>
          <h1 className="font-display text-3xl tracking-tight">ClinicalFlow</h1>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {roles.map((item) => (
            <button
              key={item.value}
              onClick={() => setRole(item.value)}
              className={cn(
                'front-desk-target flex items-center justify-center gap-2 border',
                role === item.value
                  ? 'border-[#d8ee72] bg-[#d8ee72] text-[#073d33]'
                  : 'border-white/15 bg-white/5 text-white/70 hover:bg-white/10',
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </button>
          ))}
        </div>
        <div className="rounded-2xl bg-black/20 p-4 text-center font-mono text-2xl font-bold tracking-tight">
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
                'front-desk-target rounded-xl bg-white/10 text-white hover:bg-white/15',
                key === 'login' && 'bg-[#d8ee72] text-[#073d33] hover:bg-[#e4f59b]',
                key === 'clear' && 'bg-white/5',
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
