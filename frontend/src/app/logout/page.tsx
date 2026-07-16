'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { LogOut } from 'lucide-react';
import { clearDemoSession } from '@/lib/demo-session';
import { api } from '@/lib/auth';

export default function LogoutPage() {
  useEffect(() => {
    clearDemoSession();
    void api.post('/api/v1/auth/logout', {}).finally(() => {
      window.setTimeout(() => window.location.replace('/login'), 500);
    });
  }, []);

  return (
    <main className="grid min-h-screen place-items-center bg-[#073d33] p-4 text-white">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-white p-6 text-center text-slate-900 shadow-xl">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-blue-50 text-[#0b5d4b]">
          <LogOut className="h-6 w-6" />
        </div>
        <h1 className="mt-4 text-2xl font-black">Signed out</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">Your session has been securely revoked.</p>
        <Link href="/login" className="mt-6 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#0b5d4b] px-4 py-3 text-sm font-bold text-white">
          Choose another workspace
        </Link>
      </section>
    </main>
  );
}
