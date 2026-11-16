'use client';

import { Activity, ArrowUpRight, Menu, Search, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { docsNavigation } from './docs-data';

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';

export function DocsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const allItems = useMemo(() => docsNavigation.flatMap((group) => group.items), []);
  const results = allItems.filter((item) => `${item.label} ${item.description}`.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (event.key === 'Escape') {
        setSearchOpen(false);
        setMenuOpen(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  function goTo(href: string) {
    setSearchOpen(false);
    setMenuOpen(false);
    setQuery('');
    router.push(href);
  }

  return (
    <div className="min-h-screen bg-[#07110e] text-[#d8e2dd]">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#07110e]/95 backdrop-blur-xl">
        <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
          <button type="button" onClick={() => setMenuOpen(true)} aria-label="Open documentation navigation" className="grid h-10 w-10 place-items-center rounded-lg border border-white/10 lg:hidden"><Menu className="h-5 w-5" /></button>
          <Link href="/developers" className="inline-flex items-center gap-2 font-display text-lg font-bold text-white"><span className="grid h-9 w-9 place-items-center rounded-full bg-[#d8ee72] text-[#073d33]"><Activity className="h-4 w-4" /></span>ClinicalFlow <span className="hidden rounded-md border border-white/10 px-2 py-1 font-ui text-[10px] font-bold uppercase tracking-[0.18em] text-white/45 sm:inline">Developers</span></Link>
          <nav className="ml-5 hidden items-center gap-1 border-l border-white/10 pl-5 md:flex" aria-label="Developer portal sections">
            <Link href="/developers" className={`rounded-lg px-3 py-2 text-sm font-bold ${pathname === '/developers' ? 'bg-white/10 text-white' : 'text-white/55 hover:text-white'}`}>Guides</Link>
            <Link href="/developers/api-reference" className={`rounded-lg px-3 py-2 text-sm font-bold ${pathname === '/developers/api-reference' ? 'bg-white/10 text-white' : 'text-white/55 hover:text-white'}`}>API reference</Link>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button type="button" onClick={() => setSearchOpen(true)} className="inline-flex h-10 min-w-10 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 text-sm text-white/55 hover:border-white/20 hover:text-white"><Search className="h-4 w-4" /><span className="hidden sm:inline">Search docs</span><kbd className="ml-3 hidden rounded border border-white/10 px-1.5 py-0.5 text-[10px] lg:inline">⌘K</kbd></button>
            <a href={`${apiBase}/docs`} target="_blank" rel="noreferrer" className="hidden h-10 items-center gap-2 rounded-xl bg-[#d8ee72] px-4 text-sm font-black text-[#073d33] sm:inline-flex">OpenAPI <ArrowUpRight className="h-4 w-4" /></a>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] lg:grid-cols-[292px_minmax(0,1fr)]">
        <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] overflow-y-auto border-r border-white/10 px-5 py-8 lg:block">
          <DocsNavigation pathname={pathname} />
          <div className="mt-10 rounded-2xl border border-[#d8ee72]/20 bg-[#d8ee72]/[0.06] p-4">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-[#d8ee72]">Live API</p>
            <p className="mt-2 text-sm leading-6 text-white/55">Explore request schemas and execute authorized calls in FastAPI Swagger.</p>
            <a href={`${apiBase}/docs`} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm font-black text-white">Open Swagger <ArrowUpRight className="h-4 w-4" /></a>
          </div>
        </aside>
        <main className="min-w-0">{children}</main>
      </div>

      {menuOpen ? <div className="fixed inset-0 z-[70] bg-black/65 lg:hidden" onClick={() => setMenuOpen(false)}><aside className="h-full w-[min(88vw,340px)] overflow-y-auto border-r border-white/10 bg-[#07110e] p-5" onClick={(event) => event.stopPropagation()}><div className="mb-8 flex items-center justify-between"><span className="font-display text-xl text-white">Documentation</span><button type="button" onClick={() => setMenuOpen(false)} aria-label="Close documentation navigation" className="grid h-10 w-10 place-items-center rounded-lg border border-white/10"><X className="h-5 w-5" /></button></div><DocsNavigation pathname={pathname} onNavigate={() => setMenuOpen(false)} /></aside></div> : null}

      {searchOpen ? <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/70 px-4 pt-[12vh] backdrop-blur-sm" onClick={() => setSearchOpen(false)}><div role="dialog" aria-modal="true" aria-label="Search documentation" className="w-full max-w-2xl overflow-hidden rounded-2xl border border-white/15 bg-[#0d1a16] shadow-2xl" onClick={(event) => event.stopPropagation()}><div className="flex items-center gap-3 border-b border-white/10 px-4"><Search className="h-5 w-5 text-white/40" /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search guides, APIs and architecture…" className="h-16 min-w-0 flex-1 bg-transparent text-base text-white outline-none placeholder:text-white/30" /><button type="button" onClick={() => setSearchOpen(false)} className="rounded-md border border-white/10 px-2 py-1 text-xs text-white/45">ESC</button></div><div className="max-h-[420px] overflow-y-auto p-2">{results.length ? results.map((item) => <button type="button" key={item.href} onClick={() => goTo(item.href)} className="flex w-full items-center gap-3 rounded-xl p-3 text-left hover:bg-white/[0.06]"><span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.06] text-[#d8ee72]"><item.icon className="h-5 w-5" /></span><span><span className="block font-bold text-white">{item.label}</span><span className="mt-0.5 block text-sm text-white/45">{item.description}</span></span></button>) : <p className="p-8 text-center text-sm text-white/45">No documentation pages match “{query}”.</p>}</div></div></div> : null}
    </div>
  );
}

function DocsNavigation({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return <nav aria-label="Documentation navigation" className="space-y-8">{docsNavigation.map((group) => <div key={group.title}><p className="mb-3 px-3 text-[11px] font-black uppercase tracking-[0.2em] text-white/30">{group.title}</p><div className="space-y-1">{group.items.map((item) => { const active = pathname === item.href; return <Link key={item.href} href={item.href} onClick={onNavigate} aria-current={active ? 'page' : undefined} className={`flex items-center gap-3 rounded-xl px-3 py-3 transition ${active ? 'bg-white/[0.08] text-white' : 'text-white/52 hover:bg-white/[0.04] hover:text-white'}`}><item.icon className={`h-4 w-4 shrink-0 ${active ? 'text-[#d8ee72]' : ''}`} /><span className="text-sm font-bold">{item.label}</span></Link>; })}</div></div>)}</nav>;
}

