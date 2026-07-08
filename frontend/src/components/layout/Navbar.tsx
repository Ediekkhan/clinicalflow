'use client';

import Link from 'next/link';
import { ChevronDown, Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { SignupDropdown } from '@/components/layout/SignupDropdown';

const navLinks = [
  { href: '/specialists', label: 'Specialists' },
  { href: '/hospitals', label: 'Hospitals & Clinics' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/blog', label: 'Blog' },
];

export function Navbar() {
  const [signupOpen, setSignupOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 80);
    handleScroll();
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`fixed left-0 top-0 z-50 w-full transition-all duration-300 ${scrolled ? 'border-b border-slate-100 bg-white/95 text-slate-900 backdrop-blur' : 'bg-transparent text-white'}`}>
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 md:px-6">
        <Link href="/" className="font-display text-2xl">
          <span className={scrolled ? 'text-slate-900' : 'text-white'}>Synap</span><span className="text-[#6157f5]">tiVerse</span>
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <Link key={link.href} href={link.href} className={`text-sm font-medium transition ${scrolled ? 'text-slate-600 hover:text-slate-900' : 'text-slate-300 hover:text-white'}`}>
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-2 md:flex">
          <Link href="/login" className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${scrolled ? 'text-slate-600 hover:text-slate-900' : 'text-slate-200 hover:text-white'}`}>Login</Link>
          <div className="relative">
            <button onClick={() => setSignupOpen((value) => !value)} className="inline-flex items-center gap-2 rounded-lg bg-[#6157f5] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4f46e5]">
              Sign Up For Free
              <ChevronDown className="h-4 w-4" />
            </button>
            {signupOpen ? <div className="absolute right-0 top-12"><SignupDropdown onNavigate={() => setSignupOpen(false)} /></div> : null}
          </div>
        </div>
        <button className="grid h-10 w-10 place-items-center rounded-lg border border-white/15 text-current md:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
      </div>
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-[#17173b] p-5 text-white md:hidden">
          <div className="flex items-center justify-between">
            <Link href="/" className="font-display text-2xl text-[#8f8cff]">SynaptiVerse</Link>
            <button onClick={() => setMobileOpen(false)} className="grid h-10 w-10 place-items-center rounded-lg border border-white/10" aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="mt-8 grid gap-2">
            {navLinks.map((link) => (
              <Link key={link.href} href={link.href} onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-slate-200 hover:bg-white/10">{link.label}</Link>
            ))}
            <Link href="/login" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-slate-200 hover:bg-white/10">Login</Link>
          </nav>
          <div className="mt-6"><SignupDropdown onNavigate={() => setMobileOpen(false)} /></div>
        </div>
      ) : null}
    </header>
  );
}
