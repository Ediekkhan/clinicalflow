'use client';

import { Download, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';
import { useRef, useState } from 'react';
import type { Patient } from '@/types';
import { cn } from '@/lib/utils';

function formatDob(value: string) {
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value)).toUpperCase();
}

export function PatientCard({ patient, reveal = false }: { patient: Patient; reveal?: boolean }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [saving, setSaving] = useState(false);

  function onMove(event: React.PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientY - rect.top) / rect.height - 0.5) * -10;
    const y = ((event.clientX - rect.left) / rect.width - 0.5) * 10;
    setTilt({ x, y });
  }

  async function saveCard() {
    if (!cardRef.current) return;
    setSaving(true);
    const html2canvas = (await import('html2canvas')).default;
    const canvas = await html2canvas(cardRef.current, { backgroundColor: null, scale: 2 });
    const anchor = document.createElement('a');
    anchor.href = canvas.toDataURL('image/png');
    anchor.download = `${patient.card_number}.png`;
    anchor.click();
    setSaving(false);
  }

  return (
    <div className="grid gap-5">
      <div
        ref={cardRef}
        onPointerMove={onMove}
        onPointerLeave={() => setTilt({ x: 0, y: 0 })}
        className={cn(
          'relative overflow-hidden rounded-card border border-emerald-500/30 bg-[#0D1117] p-6 text-white shadow-md transition duration-500',
          reveal && 'animate-overtake-pulse',
        )}
        style={{ transform: `perspective(900px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
      >
        <div className="absolute inset-x-0 top-0 h-1 bg-[#0D7A5F]" />
        <div className="flex items-start justify-between gap-6">
          <div>
            <p className="font-display text-2xl">SynaptiVerse</p>
            <p className="mt-1 text-sm font-bold uppercase tracking-wider text-emerald-300">◈ Health Identity Card</p>
          </div>
          <div className="h-12 w-12 rounded-full border border-emerald-400/50 bg-emerald-500/10" />
        </div>
        <div className="mt-12">
          <p className="font-display text-3xl tracking-wide">{patient.full_name.toUpperCase()}</p>
          <p className="mt-3 font-mono text-xl font-bold text-emerald-300">{patient.card_number}</p>
        </div>
        <div className="mt-10 grid gap-2 text-sm text-slate-200 sm:grid-cols-2">
          <p>DOB: {formatDob(patient.date_of_birth)} {patient.gender === 'MALE' ? '♂' : patient.gender === 'FEMALE' ? '♀' : '◇'}</p>
          <p>Registered: 07 JUN 2026</p>
        </div>
        <div className="mt-8 border-t border-emerald-400/30 pt-5 text-sm leading-6 text-slate-200">
          <span className="font-mono tracking-widest">████</span> Valid Across All Partner Clinics in Akwa Ibom
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={saveCard}
          className="touch-target inline-flex items-center justify-center gap-2 bg-[#0D7A5F] text-white hover:bg-[#096b53]"
        >
          <Download className="h-4 w-4" />
          {saving ? 'Preparing card...' : 'Save to Photos'}
        </button>
        <Link href="/dashboard" className="touch-target inline-flex items-center justify-center gap-2 border border-[#E5E7EB] bg-white text-[#111827] hover:bg-[#E6F4F0]">
          <LayoutDashboard className="h-4 w-4" />
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}

