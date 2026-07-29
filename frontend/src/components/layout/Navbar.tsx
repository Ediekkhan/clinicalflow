'use client';

import { usePathname } from 'next/navigation';
import { Activity, ArrowRight, Menu, X } from 'lucide-react';
import { useState } from 'react';

const links = [
  { href: '/specialists', label: 'For specialists' },
  { href: '/hospitals', label: 'For facilities' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/blog', label: 'Insights' },
];

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const active = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-[#073d33]/95 text-white backdrop-blur-xl">
      <div className="sv-container flex h-20 items-center justify-between">
        <a href="/" aria-label="ClinicalFlow home" className="inline-flex items-center gap-3 font-display text-xl sm:text-2xl"><span className="grid h-10 w-10 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><Activity className="h-5 w-5" /></span>ClinicalFlow</a>
        <nav aria-label="Primary navigation" className="hidden items-center gap-7 lg:flex">{links.map((link) => <a key={link.href} href={link.href} aria-current={active(link.href) ? 'page' : undefined} className={`text-sm font-bold transition ${active(link.href) ? 'text-[#d8ee72]' : 'text-white/65 hover:text-white'}`}>{link.label}</a>)}</nav>
        <div className="hidden items-center gap-2 lg:flex"><a href="/login" className="min-h-11 rounded-full px-5 py-3 text-sm font-bold text-white/80 hover:bg-white/10">Sign in</a><a href="/signup" className="sv-button-primary min-h-11 py-2">Explore workspaces <ArrowRight className="h-4 w-4" /></a></div>
        <button type="button" onClick={() => setOpen(true)} aria-label="Open menu" className="grid h-11 w-11 place-items-center rounded-full border border-white/15 lg:hidden"><Menu className="h-5 w-5" /></button>
      </div>
      {open ? <div className="fixed inset-0 z-[60] min-h-screen overflow-y-auto bg-[#073d33] p-6 lg:hidden"><div className="flex items-center justify-between"><a href="/" onClick={() => setOpen(false)} className="font-display text-2xl">ClinicalFlow</a><button type="button" onClick={() => setOpen(false)} aria-label="Close menu" className="grid h-11 w-11 place-items-center rounded-full border border-white/15"><X className="h-5 w-5" /></button></div><nav aria-label="Mobile navigation" className="mt-14 grid gap-2">{links.map((link) => <a key={link.href} href={link.href} onClick={() => setOpen(false)} className="border-b border-white/10 py-5 font-display text-3xl text-white">{link.label}</a>)}</nav><div className="mt-10 grid gap-3"><a href="/login" onClick={() => setOpen(false)} className="inline-flex min-h-12 items-center justify-center rounded-full border border-white/20 font-bold">Sign in</a><a href="/signup" onClick={() => setOpen(false)} className="sv-button-primary">Explore workspaces</a></div></div> : null}
    </header>
  );
}
