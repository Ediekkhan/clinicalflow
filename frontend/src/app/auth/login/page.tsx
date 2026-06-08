'use client';

import { useMemo, useState } from 'react';
import { ShieldCheck, Stethoscope } from 'lucide-react';
import { cn } from '@/lib/utils';

const roles = [
  { label: 'Clinic Nurse', value: 'NURSE', icon: Stethoscope },
  { label: 'System Administrator', value: 'ADMIN', icon: ShieldCheck },
] as const;

export default function LoginPage() {
  const [role, setRole] = useState<(typeof roles)[number]['value']>('NURSE');
  const [pin, setPin] = useState('');
  const masked = useMemo(() => Array.from({ length: 4 }, (_, index) => (pin[index] ? '●' : '○')).join(' '), [pin]);

  function press(value: string) {
    if (value === 'clear') {
      setPin('');
      return;
    }
    setPin((current) => (current.length < 4 ? current + value : current));
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-4 md:p-6">
      <section className="grid w-full max-w-xl gap-6 rounded-lg border border-slate-800 bg-slate-900 p-4 text-white shadow-2xl md:p-6">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-emerald-300">Secure Gateway</p>
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
                  ? 'border-emerald-500 bg-emerald-600 text-white'
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
        <div className="grid grid-cols-3 gap-3">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'clear', '0', 'login'].map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => (key === 'login' ? undefined : press(key))}
              className={cn(
                'front-desk-target bg-slate-800 text-white hover:bg-slate-700',
                key === 'login' && 'bg-emerald-600 hover:bg-emerald-700',
                key === 'clear' && 'bg-slate-700',
              )}
            >
              {key === 'login' ? 'Login' : key === 'clear' ? 'Clear' : key}
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

