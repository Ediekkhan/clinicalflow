'use client';

import Link from 'next/link';
import { CheckCircle2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { api } from '@/lib/auth';

type Plan = { id?: string; name?: string; price_label?: string; description?: string; cta_href?: string };

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [features, setFeatures] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadPricing() {
      try {
        const data = await api.get('/api/v1/public/pricing');
        if (cancelled) return;
        const payload = (data ?? {}) as { plans?: Plan[]; features?: string[] };
        setPlans(Array.isArray(payload.plans) ? payload.plans : []);
        setFeatures(Array.isArray(payload.features) ? payload.features : []);
      } catch (error) {
        console.error(error);
        if (!cancelled) {
          setPlans([]);
          setFeatures([]);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadPricing();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="bg-slate-50">
      <Navbar />
      <section className="px-6 pb-16 pt-32 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Pricing</p>
        <h1 className="font-display mx-auto mt-3 max-w-3xl text-5xl text-slate-900">Pricing for every healthcare entity</h1>
        <p className="mt-3 text-slate-500">Current plans load from the SynaptiVerse API.</p>
      </section>
      <section className="px-6 pb-20">
        <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
          {isLoading ? (
            [1, 2, 3].map((item) => <div key={item} className="h-72 animate-pulse rounded-2xl bg-white" />)
          ) : plans.length === 0 ? (
            <div className="col-span-3 rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center text-slate-500">No pricing plans available yet</div>
          ) : (
            plans.map((plan) => (
              <article key={plan.id ?? plan.name} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
                <h2 className="font-semibold text-slate-900">{plan.name}</h2>
                <p className="font-display mt-4 text-5xl text-slate-900">{plan.price_label ?? '—'}</p>
                {plan.description ? <p className="mt-4 text-sm leading-7 text-slate-600">{plan.description}</p> : null}
                <Link href={plan.cta_href ?? '/signup'} className="mt-6 inline-flex w-full justify-center rounded-xl bg-[#2563EB] px-4 py-3 text-sm font-semibold text-white">Get Started</Link>
              </article>
            ))
          )}
        </div>
        {features.length ? (
          <div className="mx-auto mt-10 max-w-4xl overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
            {features.map((feature, index) => (
              <div key={feature} className={`grid grid-cols-[1fr_auto] gap-3 px-4 py-3 text-sm ${index % 2 ? 'bg-white' : 'bg-slate-50/60'}`}>
                <span className="font-semibold text-slate-700">{feature}</span>
                <CheckCircle2 className="h-5 w-5 text-[#2563EB]" />
              </div>
            ))}
          </div>
        ) : null}
      </section>
      <Footer />
    </main>
  );
}
