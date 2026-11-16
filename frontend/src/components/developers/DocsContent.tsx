import { CheckCircle2, ExternalLink, Info, Terminal } from 'lucide-react';
import type { ReactNode } from 'react';

export function DocsPage({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: ReactNode }) {
  return <article className="mx-auto max-w-5xl px-5 py-12 sm:px-8 sm:py-16 lg:px-12"><header className="border-b border-white/10 pb-10"><p className="text-xs font-black uppercase tracking-[0.22em] text-[#d8ee72]">{eyebrow}</p><h1 className="mt-4 max-w-4xl font-display text-4xl leading-[1.04] text-white sm:text-6xl">{title}</h1><p className="mt-5 max-w-3xl text-lg leading-8 text-white/55">{description}</p></header><div className="docs-prose py-10">{children}</div></article>;
}

export function Section({ id, title, children }: { id?: string; title: string; children: ReactNode }) {
  return <section id={id} className="scroll-mt-24 border-b border-white/10 py-10 last:border-0"><h2 className="font-display text-3xl text-white sm:text-4xl">{title}</h2><div className="mt-5 space-y-5 text-[15px] leading-7 text-white/58">{children}</div></section>;
}

export function CodeBlock({ title, children }: { title?: string; children: string }) {
  return <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#030806]"><div className="border-b border-white/10 px-4 py-3"><div className="flex items-center gap-2 text-xs font-bold text-white/40"><Terminal className="h-4 w-4" />{title ?? 'Terminal'}</div></div><pre className="overflow-x-auto p-5 text-sm leading-6 text-[#c7d7d0]"><code>{children}</code></pre></div>;
}

export function Callout({ title, children, tone = 'info' }: { title: string; children: ReactNode; tone?: 'info' | 'success' }) {
  const Icon = tone === 'success' ? CheckCircle2 : Info;
  return <div className={`rounded-2xl border p-5 ${tone === 'success' ? 'border-[#d8ee72]/20 bg-[#d8ee72]/[0.06]' : 'border-sky-300/15 bg-sky-300/[0.05]'}`}><div className="flex gap-3"><Icon className={`mt-0.5 h-5 w-5 shrink-0 ${tone === 'success' ? 'text-[#d8ee72]' : 'text-sky-300'}`} /><div><p className="font-black text-white">{title}</p><div className="mt-1 text-sm leading-6 text-white/55">{children}</div></div></div></div>;
}

export function ExternalDocLink({ href, children }: { href: string; children: ReactNode }) {
  return <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-[#d8ee72] hover:text-white">{children}<ExternalLink className="h-3.5 w-3.5" /></a>;
}

