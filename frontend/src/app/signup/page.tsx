'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { getDemoDashboardRoute, isDemoRole, startDemoSession, type DemoRole } from '@/lib/demo-session';

type SignupRole = DemoRole;
type RoleTuple = readonly [SignupRole, string, string, string];

const roles: RoleTuple[] = [
  ['patient', 'Patient', 'Access triage, appointments and queue', 'PT'],
  ['specialist', 'Doctor / Specialist', 'Manage your queue and consultations', 'DR'],
  ['hospital', 'Hospital / Clinic', 'Run your facility on SynaptiVerse', 'FC'],
  ['clinic', 'Clinic', 'Manage a focused outpatient workflow', 'CL'],
  ['pharmacy', 'Pharmacy', 'Receive and fulfil prescriptions', 'RX'],
  ['lab', 'Laboratory', 'Accept referrals and release results', 'LB'],
  ['nurse', 'Nurse', 'Triage, vitals and community visits', 'NR'],
  ['hmo', 'HMO / Insurance', 'Authorizations, claims and analytics', 'HM'],
  ['moh', 'Government', 'Monitor reports, facilities, and surveillance', 'GV'],
  ['admin', 'Admin', 'Review platform operations and settings', 'AD'],
];

const specialties = [
  'Cardiology', 'Emergency Medicine', 'General Medicine', 'Family Medicine', 'Pediatrics', 'Obstetrics and Gynaecology',
  'Surgery', 'Orthopedics', 'Neurology', 'Neurosurgery', 'Psychiatry', 'Dermatology', 'Ophthalmology', 'ENT',
  'Radiology', 'Anaesthesia', 'Pathology', 'Oncology', 'Endocrinology', 'Nephrology', 'Urology', 'Pulmonology',
  'Gastroenterology', 'Hematology', 'Infectious Disease', 'Rheumatology', 'Public Health', 'Dentistry',
  'Physiotherapy', 'Nutrition and Dietetics',
];

const roleCopy: Record<SignupRole, { title: string; subtitle: string; accent: string; fields: string[] }> = {
  patient: {
    title: 'Patient demo access',
    subtitle: 'Open the patient workspace',
    accent: '#6157f5',
    fields: ['First name', 'Last name', 'Phone number', 'Date of birth'],
  },
  specialist: {
    title: 'Specialist demo access',
    subtitle: 'Open the specialist workspace',
    accent: '#2563EB',
    fields: ['First name', 'Last name', 'Registration Number'],
  },
  hospital: {
    title: 'Hospital / Clinic demo access',
    subtitle: 'Open the hospital workspace',
    accent: '#6157f5',
    fields: ['Facility name', 'Registration Number', 'Address', 'Admin email'],
  },
  clinic: {
    title: 'Clinic demo access',
    subtitle: 'Open the clinic workspace',
    accent: '#2563EB',
    fields: ['Clinic name', 'Registration Number', 'Address', 'Admin email'],
  },
  pharmacy: {
    title: 'Pharmacy demo access',
    subtitle: 'Open the pharmacy workspace',
    accent: '#7c3aed',
    fields: ['License', 'Registration', 'Pharmacy name', 'Contact phone'],
  },
  lab: {
    title: 'Laboratory demo access',
    subtitle: 'Open the laboratory workspace',
    accent: '#2563EB',
    fields: ['License', 'Laboratory name', 'Accreditation body', 'Contact email'],
  },
  nurse: {
    title: 'Nurse demo access',
    subtitle: 'Open the nurse workspace',
    accent: '#2563EB',
    fields: ['License Number', 'Full name', 'Specialty', 'Phone'],
  },
  hmo: {
    title: 'HMO / Insurance demo access',
    subtitle: 'Open the insurance workspace',
    accent: '#2563EB',
    fields: ['Organisation name', 'Accreditation', 'Estimated enrollees', 'Contact email'],
  },
  moh: {
    title: 'Government demo access',
    subtitle: 'Open the government workspace',
    accent: '#2563EB',
    fields: ['Agency name', 'Department', 'Contact email', 'Phone'],
  },
  admin: {
    title: 'Admin demo access',
    subtitle: 'Open the platform admin workspace',
    accent: '#6157f5',
    fields: ['Full name', 'Email address', 'Team', 'Access reason'],
  },
};

function AuthTop() {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 px-4 py-4 text-white sm:px-8 sm:py-5">
      <Link href="/" className="text-lg font-black tracking-wide text-[#6865ff] sm:text-xl">SynaptiVerse</Link>
      <div className="ml-auto flex flex-wrap justify-end gap-2 sm:gap-4">
        <Link href="/login" className="min-h-11 whitespace-nowrap rounded-xl border border-white/15 px-4 py-2.5 text-sm font-bold text-slate-200 sm:px-6 sm:py-3 sm:text-base">Log in</Link>
        <Link href="/hospital/waiting-room" className="min-h-11 whitespace-nowrap rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300 sm:px-6 sm:py-3 sm:text-base">Waiting room TV</Link>
      </div>
    </header>
  );
}

function useDemoLauncher() {
  const router = useRouter();
  return (role: SignupRole) => {
    startDemoSession(role);
    router.push(getDemoDashboardRoute(role));
  };
}

function RolePicker() {
  const launchDemo = useDemoLauncher();

  return (
    <main className="min-h-screen bg-[linear-gradient(110deg,#151a37,#302a73)]">
      <AuthTop />
      <section className="mx-auto max-w-[1120px] px-4 py-6 text-center text-white sm:px-6 sm:py-8 lg:py-10">
        <h1 className="text-3xl font-black sm:text-4xl">Choose a demo workspace</h1>
        <p className="mt-3 text-base text-slate-400 sm:text-lg">Tap a role to enter its dashboard</p>
        <div className="mx-auto mt-6 grid max-w-[1080px] gap-3 sm:mt-8 sm:gap-4 md:grid-cols-2 lg:grid-cols-3">
          {roles.map(([key, label, desc, icon]) => (
            <button key={key} type="button" onClick={() => launchDemo(key)} className="grid min-h-24 grid-cols-[3rem_1fr] items-center gap-4 rounded-[18px] border border-white/10 bg-white/5 p-4 text-left transition hover:bg-white/10 sm:min-h-[104px] sm:grid-cols-[3.5rem_1fr]">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white/10 text-sm font-black text-white/95 sm:h-12 sm:w-12">{icon}</span>
              <span className="min-w-0"><b className="block text-lg leading-tight text-white sm:text-xl">{label}</b><span className="mt-1.5 block text-sm leading-5 text-slate-300 sm:text-[0.95rem]">{desc}</span></span>
            </button>
          ))}
        </div>
        <p className="mt-8 text-slate-400">Need the public site? <Link href="/" className="font-bold text-white">Back home</Link></p>
      </section>
    </main>
  );
}

function RegistrationForm({ type }: { type: SignupRole }) {
  const copy = roleCopy[type];
  const launchDemo = useDemoLauncher();
  const roleMeta = roles.find((role) => role[0] === type);

  return (
    <main className="min-h-screen bg-[linear-gradient(110deg,#151a37,#302a73)]">
      <AuthTop />
      <section className="mx-auto max-w-[680px] px-4 py-10 text-center sm:px-6 sm:py-12">
        <h1 className="text-3xl font-black text-white sm:text-4xl">{copy.title}</h1>
        <p className="mt-3 text-base text-slate-400 sm:mt-4 sm:text-xl">{copy.subtitle}</p>
        <form onSubmit={(event) => { event.preventDefault(); launchDemo(type); }} className="mt-7 rounded-[24px] bg-white p-6 text-left shadow-2xl sm:mt-9 sm:rounded-[28px] sm:p-10 md:p-14">
          {type !== 'patient' ? <div className="mb-7"><h2 className="text-xl font-black">{roleMeta?.[1]}</h2><p className="text-[#526783]">{roleMeta?.[2]}</p></div> : <h2 className="mb-7 text-xl font-black">Personal info</h2>}
          <div className="grid gap-5 md:grid-cols-2">
            {copy.fields.map((label) => (
              <label key={label} className={label.length > 14 ? 'md:col-span-2' : ''}>
                <span className="mb-2 block text-sm font-bold text-[#15233a]">{label}</span>
                <input className="h-12 w-full rounded-xl border border-[#dbe3ef] px-4 text-base outline-none focus:ring-2 sm:h-14 sm:px-5 sm:text-lg" placeholder={label} style={{ '--tw-ring-color': copy.accent } as React.CSSProperties} />
              </label>
            ))}
            {type === 'specialist' ? (
              <>
                <label className="md:col-span-2">
                  <span className="mb-2 block text-sm font-bold text-[#15233a]">Specialty</span>
                  <select defaultValue="" className="h-12 w-full rounded-xl border border-[#dbe3ef] px-4 text-base outline-none sm:h-14 sm:px-5 sm:text-lg">
                    <option value="" disabled>Select specialty</option>
                    {specialties.map((specialty) => <option key={specialty}>{specialty}</option>)}
                  </select>
                </label>
                <div className="md:col-span-2">
                  <span className="mb-2 block text-sm font-bold text-[#15233a]">Practice type</span>
                  <div className="grid gap-3 md:grid-cols-3">{['Hospital-based', 'Private practice', 'Both'].map((item) => <button type="button" key={item} className="min-h-12 rounded-xl border border-[#dbe3ef] px-4 py-3 text-sm sm:text-base">{item}</button>)}</div>
                </div>
              </>
            ) : null}
            {type === 'hospital' || type === 'clinic' ? (
              <div className="md:col-span-2">
                <span className="mb-2 block text-sm font-bold text-[#15233a]">Departments</span>
                <div className="flex flex-wrap gap-3">{['Emergency', 'Cardiology', 'General OPD', 'Paediatrics', 'Obs and Gynae', 'Surgery'].map((item) => <label key={item} className="flex items-center gap-2"><input type="checkbox" />{item}</label>)}</div>
              </div>
            ) : null}
            <label className="md:col-span-2">
              <span className="mb-2 block text-sm font-bold text-[#15233a]">Password</span>
              <input type="password" className="h-12 w-full rounded-xl border border-[#dbe3ef] px-4 text-base outline-none sm:h-14 sm:px-5 sm:text-lg" />
            </label>
          </div>
          {type !== 'patient' ? <label className="mt-6 flex items-start gap-3 text-sm leading-6 text-[#526783] sm:text-base"><input type="checkbox" className="mt-1" />I agree to the Terms of Service, Privacy Policy, and Data Processing Agreement</label> : null}
          <button className="mt-8 h-14 w-full rounded-xl text-lg font-black text-white" style={{ background: copy.accent }}>Enter demo dashboard</button>
        </form>
      </section>
    </main>
  );
}

function SignupPageInner() {
  const searchParams = useSearchParams();
  const type = searchParams.get('type');
  return isDemoRole(type) ? <RegistrationForm type={type} /> : <RolePicker />;
}

export default function SignupPage() {
  return (
    <Suspense fallback={<RolePicker />}>
      <SignupPageInner />
    </Suspense>
  );
}
