'use client';

import { useEffect, useState } from 'react';
import { Check, ClipboardPlus, MessageSquare, PauseCircle, Shield, Smartphone, ToggleLeft, ToggleRight, Users, X } from 'lucide-react';
import { HospitalShell } from '@/components/HospitalShell';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';
import { cn } from '@/lib/utils';

type StaffRow = { id?: string; name?: string; role?: string; scope?: string };
type HospitalSettings = { facility_name?: string; intake_paused?: boolean; sms_route?: string; whatsapp_enabled?: boolean; staff?: StaffRow[] };
type MembershipRequest = { id: string; name: string; email?: string; department_id: string; role: string; specialty_id?: string };
type Department = { id: string; name: string };
type InvitationResult = { signup_path: string; expires_at: string };

export default function HospitalSettingsPage() {
  const [settings, setSettings] = useState<HospitalSettings>({});
  const [isLoading, setIsLoading] = useState(true);
  const [requests, setRequests] = useState<MembershipRequest[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [invite, setInvite] = useState({ email: '', department_id: '', role: 'doctor', specialty_id: '', employment_type: 'Full time' });
  const [invitationResult, setInvitationResult] = useState<InvitationResult | null>(null);
  const [staffError, setStaffError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadSettings() {
      try {
        const [data, requestData, departmentData] = await Promise.all([api.get('/api/v1/hospital/settings'), api.get('/api/v1/hospital/staff-membership-requests'), api.get('/api/v1/hospital/departments')]);
        if (!cancelled) {
          setSettings((data ?? {}) as HospitalSettings);
          setRequests(Array.isArray((requestData as { items?: MembershipRequest[] })?.items) ? (requestData as { items: MembershipRequest[] }).items : []);
          setDepartments(Array.isArray((departmentData as { items?: Department[] })?.items) ? (departmentData as { items: Department[] }).items : []);
        }
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

  async function createInvitation() {
    setStaffError('');
    setInvitationResult(null);
    try {
      setInvitationResult(await api.post('/api/v1/hospital/staff-invitations', invite) as InvitationResult);
    } catch (error) {
      setStaffError(error instanceof Error ? error.message : 'Unable to create invitation.');
    }
  }

  async function reviewMembership(id: string, decision: 'APPROVE' | 'REJECT') {
    setStaffError('');
    try {
      await api.patch(`/api/v1/hospital/staff-membership-requests/${id}`, { decision });
      setRequests((current) => current.filter((item) => item.id !== id));
    } catch (error) {
      setStaffError(error instanceof Error ? error.message : 'Unable to review membership.');
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
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-card border border-[#dbe2dc] bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2"><ClipboardPlus className="h-5 w-5 text-[#0b5d4b]" /><h2 className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Invite staff</h2></div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <input aria-label="Staff work email" placeholder="Staff work email" type="email" value={invite.email} onChange={(event) => setInvite((current) => ({ ...current, email: event.target.value }))} className="min-h-12 rounded-xl border border-[#dbe2dc] px-3" />
              <select aria-label="Department" value={invite.department_id} onChange={(event) => setInvite((current) => ({ ...current, department_id: event.target.value }))} className="min-h-12 rounded-xl border border-[#dbe2dc] px-3"><option value="">Select department</option>{departments.map((item) => <option key={item.id} value={item.name}>{item.name}</option>)}</select>
              <select aria-label="Role" value={invite.role} onChange={(event) => setInvite((current) => ({ ...current, role: event.target.value }))} className="min-h-12 rounded-xl border border-[#dbe2dc] px-3"><option value="doctor">Doctor</option><option value="specialist">Specialist</option><option value="nurse">Nurse</option></select>
              <input aria-label="Specialty or nursing focus" placeholder="Specialty or nursing focus" value={invite.specialty_id} onChange={(event) => setInvite((current) => ({ ...current, specialty_id: event.target.value }))} className="min-h-12 rounded-xl border border-[#dbe2dc] px-3" />
              <input aria-label="Employment type" placeholder="Employment type" value={invite.employment_type} onChange={(event) => setInvite((current) => ({ ...current, employment_type: event.target.value }))} className="min-h-12 rounded-xl border border-[#dbe2dc] px-3" />
              <button type="button" onClick={() => void createInvitation()} disabled={!invite.email || !invite.department_id} className="front-desk-target bg-[#0b5d4b] text-white disabled:opacity-40">Create secure invitation</button>
            </div>
            {invitationResult ? <div className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900"><p className="font-bold">Invitation created</p><p className="mt-1 break-all">{invitationResult.signup_path}</p></div> : null}
          </div>
          <div className="rounded-card border border-[#dbe2dc] bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2"><Users className="h-5 w-5 text-[#0b5d4b]" /><h2 className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Pending membership requests</h2></div>
            <div className="mt-4 grid gap-3">
              {requests.length ? requests.map((item) => <div key={item.id} className="rounded-xl border border-[#dbe2dc] p-3"><p className="font-bold text-[#10231e]">{item.name}</p><p className="text-sm text-[#60706a]">{item.department_id} · {item.role}{item.specialty_id ? ` · ${item.specialty_id}` : ''}</p><div className="mt-3 flex gap-2"><button type="button" onClick={() => void reviewMembership(item.id, 'APPROVE')} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-[#0b5d4b] px-4 text-sm font-bold text-white"><Check className="h-4 w-4" />Approve</button><button type="button" onClick={() => void reviewMembership(item.id, 'REJECT')} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-rose-200 px-4 text-sm font-bold text-rose-700"><X className="h-4 w-4" />Reject</button></div></div>) : <EmptyState title="No pending requests" body="New staff membership requests will appear here." />}
            </div>
          </div>
        </section>
        {staffError ? <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{staffError}</p> : null}
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
