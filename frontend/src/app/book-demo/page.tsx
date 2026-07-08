import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

export default function BookDemoPage() {
  return (
    <main className="bg-slate-50">
      <Navbar />
      <section className="grid min-h-screen place-items-center px-6 py-32">
        <form className="w-full max-w-xl rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Book a Demo</p>
          <h1 className="font-display mt-2 text-4xl text-slate-900">See SynaptiVerse in action</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">Tell us about your facility and our onboarding team will contact you.</p>
          <div className="mt-6 grid gap-4">
            {['Organization name', 'Work email', 'Phone number', 'Facility type'].map((label) => (
              <label key={label} className="grid gap-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>
                <input className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100" placeholder={label} />
              </label>
            ))}
            <button className="rounded-xl bg-[#2563EB] px-5 py-3 text-sm font-semibold text-white">Request Demo</button>
          </div>
        </form>
      </section>
      <Footer />
    </main>
  );
}

