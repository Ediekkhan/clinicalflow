import type { UrgencyLevel } from '@/types';
import { cn } from '@/lib/utils';

const badgeClasses: Record<UrgencyLevel, string> = {
  CRITICAL: 'border-[#FCA5A5] bg-[#FEF2F2] text-[#DC2626]',
  URGENT: 'border-[#FCD34D] bg-[#FFFBEB] text-[#D97706]',
  ROUTINE: 'border-[#93C5FD] bg-[#EFF6FF] text-[#073d33]',
};

export function UrgencyBadge({ level, className }: { level: UrgencyLevel; className?: string }) {
  return (
    <span className={cn('inline-flex min-h-6 items-center rounded-badge border px-2.5 py-1 text-xs font-bold uppercase tracking-wider', badgeClasses[level], className)}>
      {level}
    </span>
  );
}

