import { Share2 } from 'lucide-react';
import { Badge } from '@/components/shared/Badge';

export function QueueTracker() {
  return (
    <section className="mx-auto max-w-sm rounded-2xl border-t-4 border-amber-500 bg-white p-8 text-center shadow-md">
      <Badge tone="urgent">URGENT</Badge>
      <p className="mt-6 font-mono text-2xl font-bold text-slate-900">SV-AKS-2026-00412</p>
      <p className="mt-7 text-sm text-slate-500">You are</p>
      <p className="font-display text-7xl text-[#2563EB]">#3</p>
      <p className="text-sm text-slate-500">in queue</p>
      <div className="my-6 border-t border-slate-100" />
      <h3 className="font-semibold text-slate-900">Dr. Effiong Bassey</h3>
      <p className="mt-1 text-sm text-slate-500">Cardiologist - Room 4</p>
      <p className="text-xs text-slate-400">Ibom Specialist Hospital</p>
      <p className="mt-5 text-sm font-semibold text-slate-600">~35 minutes</p>
      <div className="mt-5 rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-600">● Waiting</div>
      <button className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600">
        <Share2 className="h-4 w-4" />
        Share your position
      </button>
    </section>
  );
}

