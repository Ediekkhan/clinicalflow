'use client';

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { ArrowRight, Send } from 'lucide-react';
import { SpecialistShell } from '@/components/SpecialistShell';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';

type Option = { id: string; name: string; location?: string };
type Referral = { id: string; origin_facility_id: string; destination_facility_id: string; required_capability: string; required_specialty: string; urgency: string; status: string; decision_reason?: string | null; created_at: string };

export function ReferralWorkspace() {
  const [patients, setPatients] = useState<Option[]>([]);
  const [facilities, setFacilities] = useState<Option[]>([]);
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [patientId, setPatientId] = useState('');
  const [facilityId, setFacilityId] = useState('');
  const [capability, setCapability] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [urgency, setUrgency] = useState('ROUTINE');
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [options, rows] = await Promise.all([api.get('/api/v1/referrals/options'), api.get('/api/v1/referrals')]) as [{ patients?: Option[]; facilities?: Option[] }, Referral[]];
      setPatients(Array.isArray(options?.patients) ? options.patients : []);
      setFacilities(Array.isArray(options?.facilities) ? options.facilities : []);
      setReferrals(Array.isArray(rows) ? rows : []);
    } catch (error) { setFeedback(error instanceof Error ? error.message : 'Unable to load referrals.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setFeedback('');
    try {
      await api.post('/api/v1/referrals', { patient_id: patientId, destination_facility_id: facilityId, required_capability: capability, required_specialty: specialty, urgency });
      setCapability(''); setSpecialty(''); setFeedback('Referral sent to the destination facility.'); await load();
    } catch (error) { setFeedback(error instanceof Error ? error.message : 'Unable to create referral.'); }
    finally { setSaving(false); }
  }

  return (
    <SpecialistShell>
      <header className="mb-8"><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Care coordination</p><h1 className="font-display mt-2 text-4xl text-[#10231e] sm:text-5xl">Referrals</h1><p className="mt-3 max-w-3xl text-slate-500">Send consented referrals to eligible facilities and follow destination decisions.</p></header>
      {feedback ? <p role="status" className="mb-5 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">{feedback}</p> : null}
      <section className="border-b border-slate-200 pb-8">
        <h2 className="text-lg font-bold text-slate-900">Create referral</h2>
        <form onSubmit={submit} className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <select required value={patientId} onChange={(event) => setPatientId(event.target.value)} className="rounded-xl border border-slate-200 px-4 py-3 text-sm"><option value="">Assigned patient</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.name}</option>)}</select>
          <select required value={facilityId} onChange={(event) => setFacilityId(event.target.value)} className="rounded-xl border border-slate-200 px-4 py-3 text-sm"><option value="">Destination facility</option>{facilities.map((facility) => <option key={facility.id} value={facility.id}>{facility.name}</option>)}</select>
          <input required value={capability} onChange={(event) => setCapability(event.target.value)} placeholder="Required capability" className="rounded-xl border border-slate-200 px-4 py-3 text-sm" />
          <input required value={specialty} onChange={(event) => setSpecialty(event.target.value)} placeholder="Required specialty" className="rounded-xl border border-slate-200 px-4 py-3 text-sm" />
          <div className="flex gap-2"><select value={urgency} onChange={(event) => setUrgency(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-3 text-sm"><option>ROUTINE</option><option>URGENT</option><option>CRITICAL</option></select><button disabled={saving} className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-[#0b5d4b] text-white disabled:opacity-60" aria-label="Create referral"><Send className="h-4 w-4" /></button></div>
        </form>
      </section>
      <section className="pt-8">
        {loading ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-slate-100" />)}</div> : referrals.length === 0 ? <EmptyState title="No referrals" body="Created and received referrals will appear here." /> : <div className="grid gap-3">{referrals.map((referral) => <article key={referral.id} className="rounded-xl border border-slate-200 bg-white p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{referral.required_specialty}</p><p className="mt-1 text-sm text-slate-500">{referral.required_capability}</p><p className="mt-2 flex items-center gap-2 text-xs text-slate-400"><span>{referral.origin_facility_id.slice(0, 8)}</span><ArrowRight className="h-3 w-3" /><span>{referral.destination_facility_id.slice(0, 8)}</span></p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{referral.status.replaceAll('_', ' ')}</span></div>{referral.decision_reason ? <p className="mt-3 text-sm text-slate-600">{referral.decision_reason}</p> : null}</article>)}</div>}
      </section>
    </SpecialistShell>
  );
}
