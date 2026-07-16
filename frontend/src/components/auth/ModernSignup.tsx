'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowRight, Building2, FlaskConical, HeartPulse, Landmark, Microscope, Pill, ShieldCheck, Stethoscope, UserCog, UsersRound } from 'lucide-react';
import { AuthFrame } from '@/components/auth/AuthFrame';
import { getDemoDashboardRoute, isDemoRole, startDemoSession, type DemoRole } from '@/lib/demo-session';

const roles: Array<{ role: DemoRole; label: string; detail: string; icon: typeof HeartPulse }> = [
  { role: 'patient', label: 'Patient', detail: 'Triage, appointments and queue', icon: HeartPulse },
  { role: 'specialist', label: 'Specialist', detail: 'Consultations and clinical notes', icon: Stethoscope },
  { role: 'hospital', label: 'Hospital', detail: 'Facility-wide care operations', icon: Building2 },
  { role: 'clinic', label: 'Clinic', detail: 'Focused outpatient workflows', icon: UsersRound },
  { role: 'nurse', label: 'Nurse', detail: 'Triage, vitals and visits', icon: ShieldCheck },
  { role: 'pharmacy', label: 'Pharmacy', detail: 'Prescriptions and inventory', icon: Pill },
  { role: 'lab', label: 'Laboratory', detail: 'Requests, collections and results', icon: Microscope },
  { role: 'hmo', label: 'HMO', detail: 'Members, claims and approvals', icon: UserCog },
  { role: 'moh', label: 'Government', detail: 'Reporting and surveillance', icon: Landmark },
  { role: 'admin', label: 'Platform admin', detail: 'Users, controls and health', icon: FlaskConical },
];

export function ModernSignup() {
  const router = useRouter();
  const search = useSearchParams();
  const selected = search.get('type');

  function launch(role: DemoRole) {
    startDemoSession(role);
    router.push(getDemoDashboardRoute(role));
  }

  const selectedRole = isDemoRole(selected) ? roles.find((item) => item.role === selected) : null;
  return (
    <AuthFrame eyebrow="Choose your workspace" title={selectedRole ? `Explore the ${selectedRole.label} experience.` : 'One platform. A workspace for every role.'} description="Choose a role to explore its complete workflow with safe demo data. Existing patient and staff accounts can use their dedicated sign-in route.">
      {selectedRole ? (
        <div className="max-w-lg">
          <div className="rounded-[1.75rem] border border-[#dbe2dc] bg-[#f8f9f5] p-6 sm:p-8">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><selectedRole.icon className="h-6 w-6" /></span>
            <h2 className="mt-7 text-2xl font-black text-[#10231e]">{selectedRole.label} demo</h2>
            <p className="mt-2 leading-7 text-[#60706a]">{selectedRole.detail}. No setup or personal information is required.</p>
            <button type="button" onClick={() => launch(selectedRole.role)} className="sv-button-dark mt-7 w-full">Enter demo workspace <ArrowRight className="h-4 w-4" /></button>
          </div>
          <button type="button" onClick={() => router.push('/signup')} className="mt-5 text-sm font-bold text-[#0b5d4b]">← Choose another role</button>
        </div>
      ) : (
        <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
          {roles.map(({ role, label, detail, icon: Icon }) => (
            <button key={role} type="button" onClick={() => launch(role)} className="group flex items-center gap-4 rounded-2xl border border-[#dbe2dc] bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-[#0b5d4b] hover:shadow-lg">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[#e9f6f1] text-[#0b5d4b] transition group-hover:bg-[#d8ee72] group-hover:text-[#073d33]"><Icon className="h-5 w-5" /></span>
              <span className="min-w-0 flex-1"><b className="block text-[#10231e]">{label}</b><span className="mt-1 block text-xs leading-5 text-[#60706a]">{detail}</span></span><ArrowRight className="h-4 w-4 text-[#0b5d4b]" />
            </button>
          ))}
        </div>
      )}
      <p className="mt-7 text-sm text-[#60706a]">Already registered? <a href="/login" className="font-black text-[#0b5d4b]">Sign in securely</a></p>
    </AuthFrame>
  );
}
