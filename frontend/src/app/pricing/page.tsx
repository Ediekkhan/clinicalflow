import Link from 'next/link';
import { CheckCircle2 } from 'lucide-react';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';

const pricingTiers = [
  {
    name: 'Free',
    price: '$0',
    cadence: 'forever',
    description: 'Explore the demo workspace and validate patient intake workflows before connecting a backend.',
    cta: 'Start free',
    href: '/signup',
    popular: false,
    features: ['Frontend demo access', 'Role-based dashboard previews', 'Empty states for live data', 'Basic support resources'],
  },
  {
    name: 'Pro',
    price: '$49',
    cadence: 'per month',
    description: 'For growing teams that need faster rollout, API-connected workflows, and operational visibility.',
    cta: 'Choose Pro',
    href: '/signup?type=clinic',
    popular: true,
    features: ['Everything in Free', 'Multi-role care workflows', 'Priority implementation support', 'Analytics-ready dashboard surfaces', 'Realtime notification UI'],
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    cadence: 'annual contract',
    description: 'For hospital networks, payers, and public-sector programs with advanced security and integration needs.',
    cta: 'Contact sales',
    href: '/book-demo',
    popular: false,
    features: ['Everything in Pro', 'Custom integrations', 'Dedicated onboarding', 'Security and compliance review', 'Facility-wide rollout planning'],
  },
] as const;

export default function PricingPage() {
  return (
    <main className="bg-slate-50 text-[#0F172A]">
      <Navbar />
      <section className="px-6 pb-12 pt-32 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Pricing</p>
        <h1 className="font-display mx-auto mt-3 max-w-3xl text-5xl text-[#0F172A]">Pricing for every healthcare team</h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-600">
          Start with the frontend demo today, then scale into API-connected workflows when your backend is ready.
        </p>
      </section>

      <section className="px-6 pb-24" aria-labelledby="pricing-tiers-heading">
        <div className="mx-auto max-w-6xl">
          <h2 id="pricing-tiers-heading" className="sr-only">SynaptiVerse pricing tiers</h2>
          <div className="grid gap-6 lg:grid-cols-3 lg:items-stretch">
            {pricingTiers.map((tier) => (
              <article
                key={tier.name}
                aria-labelledby={`${tier.name.toLowerCase()}-tier-title`}
                className={`relative flex rounded-lg border bg-white p-6 shadow-sm transition duration-200 ${tier.popular ? 'border-[#2563EB] shadow-blue-100 hover:scale-105 hover:shadow-xl' : 'border-slate-200 hover:-translate-y-1 hover:shadow-md'}`}
              >
                {tier.popular ? (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-[#2563EB] px-4 py-1 text-xs font-bold uppercase tracking-wide text-white">
                    Most Popular
                  </div>
                ) : null}
                <div className="flex w-full flex-col">
                  <header>
                    <h3 id={`${tier.name.toLowerCase()}-tier-title`} className="text-xl font-black text-[#0F172A]">{tier.name}</h3>
                    <p className="mt-4 flex items-end gap-2" aria-label={`${tier.name} plan price is ${tier.price} ${tier.cadence}`}>
                      <span className="font-display text-5xl font-black text-[#0F172A]">{tier.price}</span>
                      <span className="pb-2 text-sm font-semibold text-slate-500">{tier.cadence}</span>
                    </p>
                    <p className="mt-4 min-h-20 text-sm leading-7 text-slate-600">{tier.description}</p>
                  </header>

                  <ul className="mt-6 space-y-3" aria-label={`${tier.name} plan features`}>
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex gap-3 text-sm leading-6 text-slate-700">
                        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[#2563EB]" aria-hidden="true" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <footer className="mt-auto pt-8">
                    <Link
                      href={tier.href}
                      aria-label={`${tier.cta} for the ${tier.name} plan priced at ${tier.price} ${tier.cadence}`}
                      className={`inline-flex min-h-12 w-full items-center justify-center rounded-lg px-4 py-3 text-sm font-bold transition-colors duration-200 ${tier.popular ? 'bg-[#2563EB] text-white hover:bg-[#1D4ED8]' : 'bg-[#0F172A] text-white hover:bg-slate-700'}`}
                    >
                      {tier.cta}
                    </Link>
                  </footer>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
