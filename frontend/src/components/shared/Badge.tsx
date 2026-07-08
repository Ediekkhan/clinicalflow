import type { ReactNode } from 'react';

type BadgeTone = 'critical' | 'urgent' | 'routine' | 'success' | 'slate' | 'violet' | 'amber' | 'rose';

const tones: Record<BadgeTone, string> = {
  critical: 'border-rose-200 bg-rose-50 text-rose-600',
  urgent: 'border-amber-200 bg-amber-50 text-amber-600',
  routine: 'border-blue-200 bg-blue-50 text-blue-600',
  success: 'border-blue-200 bg-blue-50 text-blue-600',
  slate: 'border-slate-200 bg-slate-50 text-slate-600',
  violet: 'border-violet-200 bg-violet-50 text-violet-600',
  amber: 'border-amber-200 bg-amber-50 text-amber-600',
  rose: 'border-rose-200 bg-rose-50 text-rose-600',
};

export function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: BadgeTone }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${tones[tone]}`}>
      {children}
    </span>
  );
}
