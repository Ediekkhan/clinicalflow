'use client';

import Link from 'next/link';
import { Building, Building2, FlaskConical, Heart, Pill, Shield, Stethoscope, User } from 'lucide-react';

const items = [
  { type: 'patient', label: 'Patient', desc: 'Check symptoms & book appointments', icon: User, tone: 'sky' },
  { type: 'specialist', label: 'Doctor / Specialist', desc: 'Join our specialist network', icon: Stethoscope, tone: 'sky' },
  { type: 'hospital', label: 'Hospital', desc: 'Enterprise multi-department setup', icon: Building, tone: 'blue' },
  { type: 'clinic', label: 'Clinic', desc: 'Private or specialist clinic', icon: Building2, tone: 'blue' },
  { type: 'pharmacy', label: 'Pharmacy', desc: 'Join the prescription network', icon: Pill, tone: 'sky' },
  { type: 'lab', label: 'Laboratory', desc: 'Diagnostic & imaging centre', icon: FlaskConical, tone: 'blue' },
  { type: 'nurse', label: 'Nurse', desc: 'Community & clinical nursing', icon: Heart, tone: 'sky' },
  { type: 'hmo', label: 'HMO / Health Insurance', desc: 'Manage enrollees & providers', icon: Shield, tone: 'blue' },
] as const;

const toneClasses = {
  sky: 'bg-blue-50 text-blue-600',
  blue: 'bg-blue-50 text-blue-600',
};

export function SignupDropdown({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-2xl md:w-72">
      <p className="border-b border-slate-100 pb-3 text-xs font-bold uppercase tracking-wider text-slate-400">Register as a...</p>
      <div className="mt-3 grid gap-1">
        {items.map((item) => (
          <Link key={item.type} href={`/signup?type=${item.type}`} onClick={onNavigate} className="group flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-slate-50">
            <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${toneClasses[item.tone]}`}>
              <item.icon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800 group-hover:text-slate-900">{item.label}</p>
              <p className="text-xs text-slate-400">{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
