import SiteLayout from '@/components/layout/SiteLayout';

const sections = [
  {
    id: 'ndpa-compliance',
    title: 'NDPA Compliance',
    text: 'SynaptiVerse treats health data as sensitive personal data and keeps consent, purpose limitation, access control, and audit logging at the center of the platform.',
  },
  {
    id: 'cookie-policy',
    title: 'Cookie Policy',
    text: 'We use essential cookies for authentication, security, and session continuity. Analytics cookies are only used to improve product reliability and performance.',
  },
  {
    id: 'data-processing-agreement',
    title: 'Data Processing Agreement',
    text: 'Partner facilities remain controllers of their patient records while SynaptiVerse processes data only to provide triage, scheduling, queue, and coordination services.',
  },
];

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#f7f9fc] text-[#020b22]">
      <SiteLayout>
      <section className="mx-auto max-w-4xl px-6 pb-20 pt-32">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-[#6157f5]">Legal</p>
        <h1 className="mt-3 text-5xl font-black">Privacy Policy</h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-[#526783]">
          This page explains how SynaptiVerse protects patient, provider, and facility data across the healthcare network.
        </p>
        <div className="mt-10 grid gap-5">
          {sections.map((section) => (
            <section key={section.id} id={section.id} className="rounded-2xl border border-[#dbe3ef] bg-white p-6">
              <h2 className="text-xl font-black">{section.title}</h2>
              <p className="mt-3 leading-7 text-[#526783]">{section.text}</p>
            </section>
          ))}
        </div>
      </section>
      </SiteLayout>
    </main>
  );
}
