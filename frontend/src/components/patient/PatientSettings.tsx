'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/auth';

type SettingsForm = {
  full_name?: string;
  phone?: string;
  emergency_contact?: string;
  hmo_provider?: string;
  blood_group?: string;
  genotype?: string;
  known_allergies?: string;
  current_medications?: string;
};

const personalFields: { key: keyof SettingsForm; label: string }[] = [
  { key: 'full_name', label: 'Full name' },
  { key: 'phone', label: 'Phone number' },
  { key: 'emergency_contact', label: 'Emergency contact' },
  { key: 'hmo_provider', label: 'HMO provider' },
];

const healthFields: { key: keyof SettingsForm; label: string }[] = [
  { key: 'blood_group', label: 'Blood group' },
  { key: 'genotype', label: 'Genotype' },
  { key: 'known_allergies', label: 'Known allergies' },
  { key: 'current_medications', label: 'Current medications' },
];

export function PatientSettings() {
  const [form, setForm] = useState<SettingsForm>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadSettings() {
      try {
        const data = await api.get('/api/v1/auth/patient/me');
        if (!cancelled) setForm((data ?? {}) as SettingsForm);
      } catch (error) {
        console.error(error);
        if (!cancelled) setForm({});
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  function updateField(key: keyof SettingsForm, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveSettings() {
    setIsSaving(true);
    try {
      const data = await api.patch('/api/v1/patient/profile', form);
      setForm((data ?? form) as SettingsForm);
    } catch (error) {
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return <div className="grid gap-4 xl:grid-cols-2">{[1, 2].map((item) => <div key={item} className="h-80 animate-pulse rounded-2xl bg-slate-100" />)}</div>;
  }

  return (
    <section className="grid gap-4 xl:grid-cols-2">
      <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900">Personal profile</h3>
        <div className="mt-5 grid gap-4">
          {personalFields.map(({ key, label }) => (
            <label key={key} className="grid gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>
              <input className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#0b5d4b] focus:ring-2 focus:ring-blue-100" value={form[key] ?? ''} onChange={(event) => updateField(key, event.target.value)} placeholder={label} />
            </label>
          ))}
        </div>
      </article>
      <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900">Health information</h3>
        <div className="mt-5 grid gap-4">
          {healthFields.map(({ key, label }) => (
            <label key={key} className="grid gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>
              <input className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#0b5d4b] focus:ring-2 focus:ring-blue-100" value={form[key] ?? ''} onChange={(event) => updateField(key, event.target.value)} placeholder={label} />
            </label>
          ))}
        </div>
        <button type="button" disabled={isSaving} onClick={() => void saveSettings()} className="mt-5 rounded-xl bg-[#0b5d4b] px-5 py-3 text-sm font-semibold text-white disabled:bg-slate-300">
          Save settings
        </button>
      </article>
    </section>
  );
}
