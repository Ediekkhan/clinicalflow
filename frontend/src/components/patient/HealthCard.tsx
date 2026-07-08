'use client';

import { useRef, useState, type MouseEvent } from 'react';
import { Check, Copy, Download, RefreshCw, Share2, ShieldCheck } from 'lucide-react';

const cardNumber = 'SV-AKS-2026-00412';

const patient = {
  name: 'Adaeze Chukwu',
  dob: '15 Mar 1990',
  sex: 'F',
  location: 'Uyo, Akwa Ibom',
  validUntil: 'Jun 2027',
};

export function HealthCard() {
  const cardRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  function handleMove(event: MouseEvent<HTMLDivElement>) {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const rotateY = (x / rect.width - 0.5) * 8;
    const rotateX = (y / rect.height - 0.5) * -8;

    card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  }

  function resetTilt() {
    if (cardRef.current) {
      cardRef.current.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg)';
    }
  }

  async function copyCardNumber() {
    try {
      await navigator.clipboard?.writeText(cardNumber);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  async function shareCard() {
    if (navigator.share) {
      await navigator.share({
        title: 'SynaptiVerse Health Card',
        text: `${patient.name} - ${cardNumber}`,
      });
      return;
    }

    await copyCardNumber();
  }

  const actions = [
    { label: 'Save to Photos', icon: Download, onClick: () => window.print() },
    { label: 'Share Card', icon: Share2, onClick: shareCard },
    { label: 'Refresh Card', icon: RefreshCw, onClick: () => window.location.reload() },
  ];

  return (
    <div className="mx-auto grid w-full max-w-5xl gap-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-stretch">
      <div className="rounded-3xl border border-blue-100 bg-white p-3 shadow-sm sm:p-5">
        <div
          ref={cardRef}
          onMouseMove={handleMove}
          onMouseLeave={resetTilt}
          className="relative mx-auto aspect-[1.586] w-full max-w-[560px] overflow-hidden rounded-[1.35rem] border border-blue-400/40 bg-gradient-to-br from-[#111827] via-[#1D2464] to-[#2563EB] p-4 text-white shadow-[0_24px_70px_rgba(37,99,235,0.25)] transition-transform duration-200 sm:p-6"
        >
          <div className="absolute -right-10 -top-12 h-36 w-36 rounded-full bg-blue-300/15 sm:h-44 sm:w-44" />
          <div className="absolute -bottom-16 -left-12 h-40 w-40 rounded-full bg-white/10" />
          <div className="absolute inset-x-6 top-20 h-px bg-white/15" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.12),transparent_24%),radial-gradient(circle_at_86%_18%,rgba(147,197,253,0.2),transparent_22%)]" />

          <div className="relative z-10 flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-blue-100 sm:text-xs">
                SynaptiVerse Health Card
              </p>
              <p className="mt-1 text-xs font-semibold text-blue-100/80">Nigeria</p>
            </div>
            <div className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold">NG</div>
          </div>

          <button
            type="button"
            onClick={copyCardNumber}
            className="relative z-10 mt-8 block max-w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-left font-mono text-sm tracking-[0.14em] text-blue-100 backdrop-blur transition hover:bg-white/15 sm:mt-12 sm:text-base"
          >
            <span className="block break-all">{cardNumber}</span>
            <span className="mt-1 flex items-center gap-1 text-[10px] font-semibold tracking-normal text-blue-100/70">
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? 'Copied' : 'Tap to copy'}
            </span>
          </button>

          <div className="relative z-10 mt-5 sm:mt-8">
            <p className="font-display text-2xl leading-tight sm:text-4xl">{patient.name}</p>
            <p className="mt-2 text-xs font-semibold text-blue-100/80 sm:text-sm">
              DOB: {patient.dob} - {patient.sex} - {patient.location}
            </p>
          </div>

          <div className="absolute bottom-4 left-4 right-4 z-10 grid gap-2 text-[10px] text-blue-100/80 sm:bottom-6 sm:left-6 sm:right-6 sm:grid-cols-[1fr_auto] sm:text-xs">
            <div className="grid gap-1 sm:grid-cols-3">
              <p>
                <span className="text-white/50">VALID</span> {patient.validUntil}
              </p>
              <p>
                <span className="text-white/50">STATE</span> AKS
              </p>
              <p>
                <span className="text-white/50">TYPE</span> Patient
              </p>
            </div>
            <div className="inline-flex w-fit items-center gap-1 rounded-full bg-white/12 px-2 py-1 font-semibold text-white">
              <ShieldCheck className="h-3.5 w-3.5" />
              Verified
            </div>
          </div>
        </div>
      </div>

      <aside className="rounded-3xl border border-slate-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900">Card actions</h3>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          Keep your health identity ready for partner hospitals and clinics.
        </p>

        <div className="mt-5 grid gap-3">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.label}
                type="button"
                onClick={action.onClick}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-[#2563EB] hover:text-[#2563EB]"
              >
                <Icon className="h-4 w-4" />
                {action.label}
              </button>
            );
          })}
        </div>

        <div className="mt-5 rounded-2xl bg-blue-50 p-4 text-sm leading-6 text-blue-900">
          Your card number is the fastest way for partner facilities to find your profile, visits, and care history.
        </div>
      </aside>
    </div>
  );
}
