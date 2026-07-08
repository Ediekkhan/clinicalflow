'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';

const roles = [
  ['patient', 'Patient', 'Access triage, appointments & queue', '🙋'],
  ['specialist', 'Doctor / Specialist', 'Manage your queue & consultations', '🩺'],
  ['hospital', 'Hospital / Clinic', 'Run your facility on SynaptiVerse', '🏥'],
  ['pharmacy', 'Pharmacy', 'Receive & fulfil prescriptions', '💊'],
  ['lab', 'Laboratory', 'Accept referrals & release results', '🧪'],
  ['nurse', 'Nurse', 'Triage, vitals & community visits', '🧑‍⚕️'],
  ['hmo', 'HMO / Insurance', 'Authorizations, claims & analytics', '🛡️'],
];

const specialties = [
  'Cardiology', 'Emergency Medicine', 'General Medicine', 'Family Medicine', 'Pediatrics', 'Obstetrics & Gynaecology',
  'Surgery', 'Orthopedics', 'Neurology', 'Neurosurgery', 'Psychiatry', 'Dermatology', 'Ophthalmology', 'ENT',
  'Radiology', 'Anaesthesia', 'Pathology', 'Oncology', 'Endocrinology', 'Nephrology', 'Urology', 'Pulmonology',
  'Gastroenterology', 'Hematology', 'Infectious Disease', 'Rheumatology', 'Public Health', 'Dentistry',
  'Physiotherapy', 'Nutrition & Dietetics',
];

const roleCopy: Record<string, { title: string; subtitle: string; icon: string; accent: string; fields: [string, string][] }> = {
  patient: {
    title: 'Patient registration',
    subtitle: 'Step 1 of 3',
    icon: '🙋',
    accent: '#6157f5',
    fields: [['First name', 'Adaeze'], ['Last name', 'Chukwu'], ['Phone number', '+234 803 456 7890'], ['Date of birth', '03/15/1990']],
  },
  specialist: {
    title: 'Specialist registration',
    subtitle: 'Step 1 of 2 — Credentials',
    icon: '🩺',
    accent: '#2563EB',
    fields: [['First name', 'Okon'], ['Last name', 'Bassey'], ['MDCN Registration Number', 'MDCN/R&R/2014/08821']],
  },
  hospital: {
    title: 'Hospital / Clinic registration',
    subtitle: 'Facility verification',
    icon: '🏥',
    accent: '#6157f5',
    fields: [['Facility name', 'Ibom Specialist Hospital'], ['RC Number / CAC', 'RC-2003-00412'], ['Address', '1 Udo Udoma Ave, Uyo, Akwa Ibom'], ['Admin email', 'admin@ibomspecialist.com']],
  },
  pharmacy: {
    title: 'Pharmacy registration',
    subtitle: 'Fill in your details to register',
    icon: '💊',
    accent: '#7c3aed',
    fields: [['PCN License', 'PCN/2018/04521'], ['NAFDAC Registration', 'NAFDAC-2019-PH-0081'], ['Pharmacy name', 'Greenleaf Pharmacy Uyo'], ['Contact phone', '+234 802 345 6789']],
  },
  lab: {
    title: 'Laboratory registration',
    subtitle: 'Fill in your details to register',
    icon: '🧪',
    accent: '#2563EB',
    fields: [['MLSCN License', 'MLSCN-2020-0072'], ['Laboratory name', 'Uyo Diagnostic Centre'], ['Accreditation body', 'MLSCN / WHO'], ['Contact email', 'lab@uyodiagnostic.com']],
  },
  nurse: {
    title: 'Nurse registration',
    subtitle: 'Fill in your details to register',
    icon: '🧑‍⚕️',
    accent: '#2563EB',
    fields: [['NMCN Number', 'NMCN-2019-04821'], ['Full name', 'Blessing Effiong'], ['Specialty', 'Community Health Nursing'], ['Phone', '+234 805 123 4567']],
  },
  hmo: {
    title: 'HMO / Insurance registration',
    subtitle: 'Fill in your details to register',
    icon: '🛡️',
    accent: '#2563EB',
    fields: [['Organisation name', 'HealthGuard HMO'], ['NHIS Accreditation', 'NHIS/HMO/2016/0034'], ['Estimated enrollees', '12,000'], ['Contact email', 'ops@healthguard.ng']],
  },
};

function AuthTop() {
  return (
    <header className="flex items-center justify-between px-8 py-7 text-white">
      <Link href="/" className="text-xl font-black tracking-wide text-[#6865ff]">SynaptiVerse</Link>
      <div className="flex gap-4">
        <Link href="/login" className="rounded-xl border border-white/15 px-6 py-3 font-bold text-slate-200">Log in</Link>
        <Link href="/hospital/waiting-room" className="rounded-xl border border-white/10 px-6 py-3 text-slate-500">📺 Waiting room TV</Link>
      </div>
    </header>
  );
}

function Submitted() {
  return (
    <main className="min-h-screen bg-[linear-gradient(110deg,#121833,#2d286f)]">
      <AuthTop />
      <section className="grid place-items-center px-6 py-20">
        <div className="w-full max-w-[600px] rounded-[28px] bg-white p-14 text-center shadow-2xl">
          <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-amber-100 text-4xl">⌛</div>
          <h1 className="mt-8 text-3xl font-black">Registration submitted!</h1>
          <p className="mx-auto mt-5 max-w-md text-lg leading-7 text-[#526783]">Your credentials are under review. Verification typically takes <b>24–48 hours</b>. You'll receive an SMS and email once approved.</p>
          <div className="mt-8 rounded-2xl bg-slate-50 p-5 text-left">
            <b>What happens next</b>
            {['Our team reviews your credentials', 'Verification confirmation via SMS + email', 'Full platform access unlocked', 'Onboarding call scheduled (facilities)'].map((item, i) => (
              <p key={item} className="mt-3 text-[#12284a]"><span className="mr-3 rounded-full bg-[#6157f5] px-2 py-1 text-xs font-bold text-white">{i + 1}</span>{item}</p>
            ))}
          </div>
          <Link href="/" className="mt-8 block rounded-xl bg-[#6157f5] px-6 py-4 font-black text-white">Back to home →</Link>
        </div>
      </section>
    </main>
  );
}

function RolePicker() {
  return (
    <main className="min-h-screen bg-[linear-gradient(110deg,#151a37,#302a73)]">
      <AuthTop />
      <section className="mx-auto max-w-[840px] px-6 py-24 text-center text-white">
        <h1 className="text-4xl font-black">Create your account</h1>
        <p className="mt-5 text-lg text-slate-400">Choose your role to get started</p>
        <div className="mt-10 grid gap-4 md:grid-cols-2">
          {roles.map(([key, label, desc, icon]) => (
            <Link key={key} href={`/signup?type=${key}`} className="flex items-center gap-4 rounded-[18px] border border-white/10 bg-white/5 p-5 text-left transition hover:bg-white/10">
              <span className="grid h-12 w-12 place-items-center rounded-xl bg-white/10 text-2xl">{icon}</span>
              <span><b className="text-lg text-white">{label}</b><span className="mt-1 block text-sm text-slate-400">{desc}</span></span>
            </Link>
          ))}
        </div>
        <p className="mt-8 text-slate-400">Already have an account? <Link href="/login" className="font-bold text-white">Log in →</Link></p>
      </section>
    </main>
  );
}

function RegistrationForm({ type }: { type: string }) {
  const copy = roleCopy[type] ?? roleCopy.patient;
  const [submitted, setSubmitted] = useState(false);
  if (submitted) return <Submitted />;

  return (
    <main className="min-h-screen bg-[linear-gradient(110deg,#151a37,#302a73)]">
      <AuthTop />
      <section className="mx-auto max-w-[680px] px-6 py-12 text-center">
        <h1 className="text-4xl font-black text-white">{copy.title}</h1>
        <p className="mt-4 text-xl text-slate-400">{copy.subtitle}</p>
        <form onSubmit={(event) => { event.preventDefault(); setSubmitted(true); }} className="mt-9 rounded-[28px] bg-white p-14 text-left shadow-2xl">
          {type === 'patient' ? (
            <div className="mb-8 grid grid-cols-3 gap-2">
              <span className="h-1 rounded bg-[#6157f5]" /><span className="h-1 rounded bg-slate-200" /><span className="h-1 rounded bg-slate-200" />
            </div>
          ) : type === 'specialist' ? (
            <div className="mb-8 grid grid-cols-2 gap-2"><span className="h-1 rounded bg-[#2563EB]" /><span className="h-1 rounded bg-slate-200" /></div>
          ) : null}
          {type !== 'patient' ? <div className="mb-7 flex items-center gap-4"><span className="grid h-14 w-14 place-items-center rounded-xl bg-slate-100 text-3xl">{copy.icon}</span><div><h2 className="text-xl font-black">{roles.find((r) => r[0] === type)?.[1]}</h2><p className="text-[#526783]">{roles.find((r) => r[0] === type)?.[2]}</p></div></div> : <h2 className="mb-7 text-xl font-black">Personal info</h2>}
          <div className="grid gap-5 md:grid-cols-2">
            {copy.fields.map(([label, value]) => (
              <label key={label} className={label.length > 14 ? 'md:col-span-2' : ''}>
                <span className="mb-2 block text-sm font-bold text-[#15233a]">{label}</span>
                <input defaultValue={value} className="h-14 w-full rounded-xl border border-[#dbe3ef] px-5 text-lg outline-none focus:ring-2" style={{ '--tw-ring-color': copy.accent } as React.CSSProperties} />
              </label>
            ))}
            {type === 'specialist' ? (
              <>
                <label className="md:col-span-2">
                  <span className="mb-2 block text-sm font-bold text-[#15233a]">Specialty</span>
                  <select defaultValue="Cardiology" className="h-14 w-full rounded-xl border border-[#dbe3ef] px-5 text-lg outline-none">
                    {specialties.map((specialty) => <option key={specialty}>{specialty}</option>)}
                  </select>
                </label>
                <div className="md:col-span-2">
                  <span className="mb-2 block text-sm font-bold text-[#15233a]">Practice type</span>
                  <div className="grid gap-3 md:grid-cols-3">{['Hospital-based', 'Private practice', 'Both'].map((item, index) => <button type="button" key={item} className={`rounded-xl border px-4 py-3 ${index === 0 ? 'border-[#2563EB] bg-blue-50 text-[#2563EB]' : 'border-[#dbe3ef]'}`}>{item}</button>)}</div>
                </div>
              </>
            ) : null}
            {type === 'hospital' ? (
              <div className="md:col-span-2">
                <span className="mb-2 block text-sm font-bold text-[#15233a]">Departments</span>
                <div className="flex flex-wrap gap-3">{['Emergency', 'Cardiology', 'General OPD', 'Paediatrics', 'Obs & Gynae', 'Surgery'].map((item, i) => <label key={item} className="flex items-center gap-2"><input type="checkbox" defaultChecked={i < 4} />{item}</label>)}</div>
              </div>
            ) : null}
            <label className="md:col-span-2">
              <span className="mb-2 block text-sm font-bold text-[#15233a]">Password</span>
              <input defaultValue="password" type="password" className="h-14 w-full rounded-xl border border-[#dbe3ef] px-5 text-lg outline-none" />
            </label>
          </div>
          {type !== 'patient' ? <label className="mt-6 flex items-start gap-3 text-[#526783]"><input type="checkbox" defaultChecked className="mt-1" />I agree to the Terms of Service, Privacy Policy, and Data Processing Agreement</label> : null}
          <button className="mt-8 h-14 w-full rounded-xl text-lg font-black text-white" style={{ background: copy.accent }}>{type === 'patient' ? 'Continue →' : 'Submit registration →'}</button>
        </form>
      </section>
    </main>
  );
}

function SignupPageInner() {
  const searchParams = useSearchParams();
  const type = searchParams.get('type');
  return type ? <RegistrationForm type={type} /> : <RolePicker />;
}

export default function SignupPage() {
  return (
    <Suspense fallback={<RolePicker />}>
      <SignupPageInner />
    </Suspense>
  );
}
