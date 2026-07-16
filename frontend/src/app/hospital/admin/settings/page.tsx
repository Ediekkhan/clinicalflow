'use client';

import { useEffect, useState } from 'react';
import { MessageSquare, PauseCircle, Shield, Smartphone, ToggleLeft, ToggleRight, Users } from 'lucide-react';
import { HospitalShell } from '@/components/HospitalShell';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';
import { cn } from '@/lib/utils';

type StaffRow = { id?: string; name?: string; role?: string; scope?: string };
type HospitalSettings = { facility_name?: string; intake_paused?: boolean; sms_route?: string; whatsapp_enabled?: boolean; staff?: StaffRow[] };

export default function HospitalSettingsPage() {
  const [settings, setSettings] = useState<HospitalSettings>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadSettings() {
      try {
        const data = await api.get('/api/v1/hospital/settings');
        if (!cancelled) setSettings((data ?? {}) as HospitalSettings);
      } catch (error) {
        console.error(error);
        if (!cancelled) setSettings({});
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  async function patchSettings(payload: Partial<HospitalSettings>) {
    setSettings((current) => ({ ...current, ...payload }));
    try {
      const data = await api.patch('/api/v1/hospital/settings', payload);
      setSettings((data ?? {}) as HospitalSettings);
    } catch (error) {
      console.error(error);
    }
  }

  const paused = Boolean(settings.intake_paused);
  const whatsappEnabled = settings.whatsapp_enabled ?? false;
  const smsRoutes = settings.sms_route ? [settings.sms_route] : [];

  return (
    <HospitalShell>
      <main className="mx-auto grid max-w-7xl gap-5 p-4 md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Hospital Settings</p>
          <h1 className="font-display text-4xl text-[#10231e] md:text-5xl">{settings.facility_name ? `${settings.facility_name} account controls` : 'Account controls'}</h1>
        </div>
        {isLoading ? <div className="h-24 animate-pulse rounded-card bg-slate-100" /> : null}
        <section className="rounded-card border border-[#dbe2dc] bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <PauseCircle className="h-6 w-6 text-[#DC2626]" />
              <div>
                <h2 className="text-sm font-bold text-[#10231e]">Global intake pause</h2>
                <p className="text-sm text-[#60706a]">Stops patient triage intake for this hospital tenant.</p>
              </div>
            </div>
            <button onClick={() => void patchSettings({ intake_paused: !paused })} className={cn('front-desk-target inline-flex items-center gap-2', paused ? 'bg-[#DC2626] text-white' : 'bg-[#0b5d4b] text-white')}>
              {paused ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
              {paused ? 'Paused' : 'Active'}
            </button>
          </div>
        </section>
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-card border border-[#dbe2dc] bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-[#0b5d4b]" />
              <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">SMS Route</p>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {smsRoutes.length ? smsRoutes.map((route) => (
                <button key={route} className="front-desk-target border border-[#0b5d4b] bg-[#e9f6f1] text-[#0b5d4b]">{route}</button>
              )) : <p className="text-sm text-[#60706a]">No SMS route configured</p>}
            </div>
          </div>
          <div className="rounded-card border border-[#dbe2dc] bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-[#0b5d4b]" />
                <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">WhatsApp Intake</p>
              </div>
              <button onClick={() => void patchSettings({ whatsapp_enabled: !whatsappEnabled })} className="rounded-lg p-3 text-[#0b5d4b] hover:bg-[#e9f6f1]" aria-label="Toggle WhatsApp channel">
                {whatsappEnabled ? <ToggleRight className="h-6 w-6" /> : <ToggleLeft className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </section>
        <section className="rounded-card border border-[#dbe2dc] bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-[#0b5d4b]" />
            <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Hospital Staff</p>
          </div>
          {settings.staff?.length ? (
            <div className="mt-4 overflow-hidden rounded-card border border-[#dbe2dc]">
              {settings.staff.map((staff) => (
                <div key={staff.id ?? staff.name} className="data-row grid gap-2 border-b border-[#dbe2dc] last:border-b-0 sm:grid-cols-3">
                  <span className="font-medium text-[#10231e]">{staff.name}</span>
                  <span className="inline-flex items-center gap-2 text-[#60706a]">
                    <Shield className="h-4 w-4" />
                    {staff.role}
                  </span>
                  <span className="text-[#60706a]">{staff.scope}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4"><EmptyState title="No staff available" body="Staff records will appear here when returned by the API." /></div>
          )}
        </section>
      </main>
    </HospitalShell>
  );
}
