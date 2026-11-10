'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ArrowRight, Building2, FlaskConical, HeartPulse, Landmark, Microscope, Pill, ShieldCheck, Stethoscope, UserCog, UsersRound } from 'lucide-react';
import { AuthFrame } from '@/components/auth/AuthFrame';

type WorkspaceRole = 'patient' | 'specialist' | 'hospital' | 'clinic' | 'pharmacy' | 'lab' | 'nurse' | 'hmo' | 'moh' | 'admin';

type Workspace = {
  role: WorkspaceRole;
  label: string;
  detail: string;
  icon: typeof HeartPulse;
  loginHref: string;
};

const signupRoutes: Record<WorkspaceRole, string> = {
  patient: '/signup/patient', specialist: '/signup/specialist', hospital: '/signup/hospital', clinic: '/signup/clinic',
  pharmacy: '/signup/pharmacy', lab: '/signup/laboratory', nurse: '/signup/nurse', hmo: '/signup/hmo',
  moh: '/signup/government', admin: '/signup/platform-admin',
};
const roles: Workspace[] = [
  { role: 'patient', label: 'Patient', detail: 'Triage, appointments and queue', icon: HeartPulse, loginHref: '/login' },
  { role: 'specialist', label: 'Specialist', detail: 'Consultations and clinical notes', icon: Stethoscope, loginHref: '/specialist/login' },
  { role: 'hospital', label: 'Hospital', detail: 'Facility-wide care operations', icon: Building2, loginHref: '/hospital/login' },
  { role: 'clinic', label: 'Clinic', detail: 'Focused outpatient workflows', icon: UsersRound, loginHref: '/auth/login' },
  { role: 'nurse', label: 'Nurse', detail: 'Triage, vitals and visits', icon: ShieldCheck, loginHref: '/auth/login' },
  { role: 'pharmacy', label: 'Pharmacy', detail: 'Prescriptions and inventory', icon: Pill, loginHref: '/auth/login' },
  { role: 'lab', label: 'Laboratory', detail: 'Requests, collections and results', icon: Microscope, loginHref: '/auth/login' },
  { role: 'hmo', label: 'HMO', detail: 'Members, claims and approvals', icon: UserCog, loginHref: '/auth/login' },
  { role: 'moh', label: 'Government', detail: 'Reporting and surveillance', icon: Landmark, loginHref: '/auth/login' },
  { role: 'admin', label: 'Platform admin', detail: 'Users, controls and health', icon: FlaskConical, loginHref: '/auth/login' },
];

export function ModernSignup() {
  const search = useSearchParams();
  const requestedType = search.get('type');
  const selectedType = requestedType === 'laboratory' ? 'lab' : requestedType;
  const selectedRole = roles.find((item) => item.role === selectedType);

  return (
    <AuthFrame
      eyebrow="Choose your workspace"
      title={selectedRole ? `Access the ${selectedRole.label} workspace.` : 'One platform. A workspace for every role.'}
      description="Choose your role to sign in with an approved account. New organization accounts are created through the onboarding process."
    >
      {selectedRole ? (
        <div className="max-w-lg">
          <div className="rounded-[1.75rem] border border-[#dbe2dc] bg-[#f8f9f5] p-6 sm:p-8">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><selectedRole.icon className="h-6 w-6" /></span>
            <h2 className="mt-7 text-2xl font-black text-[#10231e]">{selectedRole.label} account access</h2>
            <p className="mt-2 leading-7 text-[#60706a]">{selectedRole.detail}. Continue with credentials issued for this workspace.</p>
            <Link href={signupRoutes[selectedRole.role]} className="sv-button-dark mt-7 w-full">Begin onboarding <ArrowRight className="h-4 w-4" /></Link>
            <Link href={selectedRole.loginHref} className="mt-3 inline-flex min-h-12 w-full items-center justify-center rounded-full border border-[#dbe2dc] bg-white px-5 text-sm font-bold text-[#10231e]">I already have an account</Link>
          </div>
          <Link href="/signup" className="mt-5 inline-flex text-sm font-bold text-[#0b5d4b]">← Choose another role</Link>
        </div>
      ) : (
        <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
          {roles.map(({ role, label, detail, icon: Icon }) => (
            <Link key={role} href={signupRoutes[role]} className="group flex items-center gap-4 rounded-2xl border border-[#dbe2dc] bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-[#0b5d4b] hover:shadow-lg">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[#e9f6f1] text-[#0b5d4b] transition group-hover:bg-[#d8ee72] group-hover:text-[#073d33]"><Icon className="h-5 w-5" /></span>
              <span className="min-w-0 flex-1"><b className="block text-[#10231e]">{label}</b><span className="mt-1 block text-xs leading-5 text-[#60706a]">{detail}</span></span>
              <ArrowRight className="h-4 w-4 text-[#0b5d4b]" />
            </Link>
          ))}
        </div>
      )}
      <p className="mt-7 text-sm text-[#60706a]">Already registered? <Link href="/login" className="font-black text-[#0b5d4b]">Sign in securely</Link></p>
    </AuthFrame>
  );
}
