import Link from 'next/link';
import { BarChart2, Kanban, MessageSquare, Shield, Users, Workflow } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

export default function HospitalsPage() {
  return (
    <main className="bg-slate-50">
      <Navbar />
      <section className="bg-[#0D1117] px-6 pb-20 pt-32 text-white">
        <div className="mx-auto max-w-6xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-300">For Hospitals & Clinics</p>
          <h1 className="font-display mt-4 max-w-4xl text-5xl leading-tight md:text-7xl">Power your hospital&apos;s patient intake with AI</h1>
          <div className="mt-8 flex flex-wrap gap-3 text-sm text-blue-100">
            {['Live Kanban', 'Specialist Routing', 'NDPA Compliant', 'WhatsApp Integration'].map((pill) => (
              <span key={pill} className="rounded-full border border-blue-800 bg-blue-950 px-4 py-2">{pill}</span>
            ))}
          </div>
          <Link href="/book-demo" className="mt-8 inline-flex rounded-xl bg-[#2563EB] px-6 py-3.5 font-semibold text-white">Book a Demo</Link>
        </div>
      </section>
      <section className="px-6 py-20">
        <div className="mx-auto grid max-w-6xl gap-4 md:grid-cols-2 xl:grid-cols-3">
          {([
            ['AI Intake', 'Patients are triaged before arriving at reception.', MessageSquare],
            ['Queue Board', 'Departments see live queue pressure and urgent cases.', Kanban],
            ['Specialist Routing', 'Patients go to the right doctor the first time.', Workflow],
            ['Staff Roles', 'Nurses, doctors, admins, and managers have separate tools.', Users],
            ['Compliance', 'Audit logging and tenant isolation are built in.', Shield],
            ['Analytics', 'Track wait times, condition mix, and utilization from API data.', BarChart2],
          ] as const).map(([title, body, Icon]) => (
            <article key={String(title)} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <Icon className="h-7 w-7 text-[#2563EB]" />
              <h2 className="mt-4 font-semibold text-slate-900">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">{body}</p>
            </article>
          ))}
        </div>
      </section>
      <Footer />
    </main>
  );
}
