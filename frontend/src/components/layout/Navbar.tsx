'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown, Menu, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { SignupDropdown } from '@/components/layout/SignupDropdown';

const SIGNUP_DROPDOWN_TIMEOUT_MS = 120_000;

const navLinks = [
  { href: '/specialists', label: 'Specialists' },
  { href: '/hospitals', label: 'Hospitals & Clinics' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/blog', label: 'Blog' },
];

export function Navbar() {
  const pathname = usePathname();
  const [signupOpen, setSignupOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const timeoutRef = useRef<number | null>(null);

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  useEffect(() => {
    if (!signupOpen) {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      return;
    }

    const dropdown = dropdownRef.current;
    const closeDropdown = () => setSignupOpen(false);
    const resetTimer = () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
      timeoutRef.current = window.setTimeout(closeDropdown, SIGNUP_DROPDOWN_TIMEOUT_MS);
    };
    const trackedEvents = ['mousemove', 'keydown', 'click', 'touchstart'] as const;

    resetTimer();
    trackedEvents.forEach((eventName) => dropdown?.addEventListener(eventName, resetTimer));

    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      trackedEvents.forEach((eventName) => dropdown?.removeEventListener(eventName, resetTimer));
    };
  }, [signupOpen]);

  return (
    <header className="fixed left-0 top-0 z-50 w-full border-b border-slate-200 bg-white/95 text-[#0F172A] shadow-sm backdrop-blur transition-colors duration-200">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 md:px-6">
        <Link href="/" className="font-display text-2xl font-black tracking-tight" aria-label="SynaptiVerse home">
          <span className="text-[#0F172A]">Synap</span><span className="text-[#2563EB]">tiVerse</span>
        </Link>
        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary navigation">
          {navLinks.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? 'page' : undefined}
                className={`text-sm font-semibold transition-colors duration-200 ${active ? 'text-[#2563EB]' : 'text-slate-600 hover:text-[#2563EB]'}`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="hidden items-center gap-2 md:flex">
          <Link href="/login" className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 transition-colors duration-200 hover:text-[#2563EB]">Login</Link>
          <div className="relative">
            <button
              type="button"
              onClick={() => setSignupOpen((value) => !value)}
              aria-expanded={signupOpen}
              aria-haspopup="menu"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2 text-sm font-semibold text-white transition-colors duration-200 hover:bg-[#1D4ED8]"
            >
              Sign up for free
              <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${signupOpen ? 'rotate-180' : ''}`} />
            </button>
            {signupOpen ? (
              <div ref={dropdownRef} className="absolute right-0 top-12" role="menu" aria-label="Choose sign-up role">
                <SignupDropdown onNavigate={() => setSignupOpen(false)} />
              </div>
            ) : null}
          </div>
        </div>
        <button className="grid h-10 w-10 place-items-center rounded-lg border border-slate-200 text-[#0F172A] md:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
      </div>
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-white p-5 text-[#0F172A] md:hidden">
          <div className="flex items-center justify-between">
            <Link href="/" className="font-display text-2xl font-black tracking-tight" onClick={() => setMobileOpen(false)} aria-label="SynaptiVerse home">
              <span className="text-[#0F172A]">Synap</span><span className="text-[#2563EB]">tiVerse</span>
            </Link>
            <button onClick={() => setMobileOpen(false)} className="grid h-10 w-10 place-items-center rounded-lg border border-slate-200" aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="mt-8 grid gap-2" aria-label="Mobile navigation">
            {navLinks.map((link) => {
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={active ? 'page' : undefined}
                  className={`rounded-lg px-3 py-3 text-sm font-semibold transition-colors duration-200 ${active ? 'bg-blue-50 text-[#2563EB]' : 'text-slate-700 hover:bg-slate-50 hover:text-[#2563EB]'}`}
                >
                  {link.label}
                </Link>
              );
            })}
            <Link href="/login" onClick={() => setMobileOpen(false)} className="rounded-lg px-3 py-3 text-sm font-semibold text-slate-700 transition-colors duration-200 hover:bg-slate-50 hover:text-[#2563EB]">Login</Link>
          </nav>
          <div className="mt-6"><SignupDropdown onNavigate={() => setMobileOpen(false)} /></div>
        </div>
      ) : null}
    </header>
  );
}