import type { LucideIcon } from 'lucide-react';

type StatCardProps = {
  title: string;
  value: string;
  sub?: string;
  tone?: 'amber' | 'rose' | 'sky' | 'slate' | 'violet';
  icon?: LucideIcon;
};

const toneMap = {
  amber: 'border-amber-100 bg-amber-50/70 text-amber-600',
  rose: 'border-rose-100 bg-rose-50/70 text-rose-600',
  sky: 'border-blue-100 bg-blue-50/70 text-blue-600',
  slate: 'border-slate-100 bg-white text-slate-600',
  violet: 'border-violet-100 bg-violet-50/70 text-violet-600',
};

export function StatCard({ title, value, sub, tone = 'slate', icon: Icon }: StatCardProps) {
  return (
    <article className={`rounded-[22px] border p-8 ${toneMap[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#8a97b4]">{title}</p>
          <p className="mt-3 text-4xl font-black tracking-normal text-[#020b22]">{value}</p>
        </div>
        {Icon ? (
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/70">
            <Icon className="h-5 w-5" />
          </div>
        ) : null}
      </div>
      {sub ? <p className="mt-3 text-base font-medium">{sub}</p> : null}
    </article>
  );
}
