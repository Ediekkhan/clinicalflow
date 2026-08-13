'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import SiteLayout from '@/components/layout/SiteLayout';
import { api } from '@/lib/auth';

export default function BillingCheckoutPage() {
  const [state, setState] = useState<'loading' | 'ready' | 'disabled' | 'error'>('loading');
  const [message, setMessage] = useState('');
  useEffect(() => { api.get('/api/v1/billing/status').then((value) => { const data = value as { enabled?: boolean }; setState(data.enabled ? 'ready' : 'disabled'); }).catch((error) => { setState('error'); setMessage(error instanceof Error ? error.message : 'You must be an authorized organization administrator.'); }); }, []);
  async function beginCheckout() { setState('loading'); try { const result = await api.post('/api/v1/billing/checkout', { plan: 'pro' }) as { checkout_url?: string }; if (result.checkout_url) window.location.assign(result.checkout_url); } catch (error) { setState('disabled'); setMessage(error instanceof Error ? error.message : 'Billing is not configured.'); } }
  return <main className="bg-slate-50"><SiteLayout><section className="grid min-h-screen place-items-center px-6 py-32"><div className="w-full max-w-xl rounded-2xl bg-white p-8 shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Pro subscription</p><h1 className="font-display mt-3 text-4xl">Upgrade your organization</h1><p className="mt-4 text-slate-600">Secure checkout is handled by the configured payment provider. Payment confirmation comes from a verified backend webhook.</p>{state === 'disabled' || state === 'error' ? <div className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">{message || 'Billing is not configured yet. An administrator must configure the payment provider before checkout can begin.'}</div> : null}<div className="mt-8 flex gap-3"><button onClick={() => void beginCheckout()} disabled={state !== 'ready'} className="min-h-12 rounded-xl bg-[#0b5d4b] px-5 font-bold text-white disabled:cursor-not-allowed disabled:opacity-40">Continue to secure checkout</button><Link href="/pricing" className="inline-flex min-h-12 items-center rounded-xl border border-slate-200 px-5 font-bold">Back</Link></div></div></section></SiteLayout></main>;
}
