"use client";

import { useEffect, useState } from 'react';
import { api } from '@/lib/auth';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';

type PatientProfile = { card_number?: string };

export function PatientShell({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      try {
        const data = await api.get('/api/v1/auth/patient/me');
        if (!cancelled) setProfile((data ?? null) as PatientProfile | null);
      } catch (error) {
        console.error(error);
        if (!cancelled) setProfile(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadProfile();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#F7F8FA] pt-20">
      <Navbar />

      <main className="mx-auto max-w-7xl p-4 md:p-6">
        {isLoading ? (
          <div className="mb-4 h-4 w-36 animate-pulse rounded bg-slate-100" />
        ) : profile?.card_number ? (
          <div className="mb-4 inline-flex max-w-full rounded-badge bg-[#e0f2fe] px-3 py-1 font-mono text-xs font-bold text-[#2563EB]">
            <span className="truncate">{profile.card_number}</span>
          </div>
        ) : null}

        {children}
      </main>

      <Footer />
    </div>
  );
}
