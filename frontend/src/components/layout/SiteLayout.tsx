"use client";

import React from 'react';
import { Navbar } from './Navbar';
import { Footer } from './Footer';

export function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f4f5ef] pt-20">
      <a href="#main-content" className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-lg bg-white px-4 py-3 font-semibold text-blue-700 shadow-lg transition focus:translate-y-0">Skip to main content</a>
      <Navbar />
      <main id="main-content" tabIndex={-1} className="mx-auto max-w-7xl p-4 md:p-6">{children}</main>
      <Footer />
    </div>
  );
}

export default SiteLayout;
