import { Activity, HeartPulse, ShieldAlert } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

const posts = [
  ['Triage Guide', 'How to Know When Your Fever Is a Medical Emergency', 'Not all fevers are equal. Learn signs that need immediate emergency care in Nigeria.', 'June 10, 2026', ShieldAlert],
  ['Disease Guide', 'Malaria vs Typhoid: How to Tell the Difference', 'Both are common in Nigeria and share symptoms. Here is what our AI looks for.', 'June 5, 2026', Activity],
  ['Women’s Health', 'Preeclampsia: The Silent Danger in Nigerian Pregnancies', 'Knowing early signs could save your life or someone you love.', 'May 28, 2026', HeartPulse],
] as const;

export default function BlogPage() {
  return (
    <main className="bg-slate-50">
      <Navbar />
      <section className="px-6 pb-16 pt-32 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Health Insights</p>
        <h1 className="font-display mt-3 text-5xl text-slate-900">Latest health updates</h1>
      </section>
      <section className="px-6 pb-20">
        <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
          {posts.map(([category, title, excerpt, date, Icon]) => (
            <article key={String(title)} className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm transition hover:shadow-md">
              <div className="grid h-48 place-items-center bg-gradient-to-br from-blue-50 to-slate-100 text-[#2563EB]"><Icon className="h-14 w-14 opacity-40" /></div>
              <div className="p-5">
                <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#2563EB]">{category}</span>
                <p className="mt-4 text-xs text-slate-400">{date}</p>
                <h2 className="mt-2 font-semibold leading-snug text-slate-900">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">{excerpt}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <Footer />
    </main>
  );
}
