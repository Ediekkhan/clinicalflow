import Link from 'next/link';
import SiteLayout from '@/components/layout/SiteLayout';

export default async function ConfirmationPage({ searchParams }: { searchParams: Promise<{ reference?: string }> }) {
  const params = await searchParams;
  return <main className="bg-slate-50"><SiteLayout><section className="grid min-h-screen place-items-center px-6 py-32"><div className="w-full max-w-xl rounded-2xl bg-white p-10 text-center shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Enquiry received</p><h1 className="font-display mt-3 text-4xl text-slate-900">Thank you for contacting us.</h1><p className="mt-4 text-slate-600">Your reference is <strong>{params.reference ?? 'pending'}</strong>. Our team will review your request and follow up.</p><Link href="/" className="mt-8 inline-flex rounded-xl bg-[#0b5d4b] px-6 py-3 font-semibold text-white">Return home</Link></div></section></SiteLayout></main>;
}
