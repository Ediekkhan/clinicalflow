import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

const sections = [
  {
    title: 'Platform Use',
    text: 'SynaptiVerse helps healthcare teams coordinate triage, queues, appointments, pharmacy fulfillment, laboratory workflows, and reporting.',
  },
  {
    title: 'Clinical Responsibility',
    text: 'AI triage and workflow recommendations support care teams, but licensed clinicians and approved facilities remain responsible for diagnosis and treatment decisions.',
  },
  {
    id: 'refund-policy',
    title: 'Refund Policy',
    text: 'Paid subscriptions can be reviewed with support for billing errors, duplicate charges, or service interruptions according to the customer agreement.',
  },
];

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-[#f7f9fc] text-[#020b22]">
      <Navbar />
      <section className="mx-auto max-w-4xl px-6 pb-20 pt-32">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-[#6157f5]">Legal</p>
        <h1 className="mt-3 text-5xl font-black">Terms of Service</h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-[#526783]">
          These terms outline the baseline rules for using SynaptiVerse across patients, providers, facilities, and partners.
        </p>
        <div className="mt-10 grid gap-5">
          {sections.map((section) => (
            <section key={section.title} id={section.id} className="rounded-2xl border border-[#dbe3ef] bg-white p-6">
              <h2 className="text-xl font-black">{section.title}</h2>
              <p className="mt-3 leading-7 text-[#526783]">{section.text}</p>
            </section>
          ))}
        </div>
      </section>
      <Footer />
    </main>
  );
}
