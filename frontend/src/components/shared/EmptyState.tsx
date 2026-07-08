import { PackageCheck, type LucideIcon } from 'lucide-react';

export function EmptyState({ icon: Icon = PackageCheck, title, body }: { icon?: LucideIcon; title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center">
      <Icon className="mx-auto h-8 w-8 text-[#2563EB]" />
      <h2 className="mt-4 text-lg font-bold text-slate-900">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">{body}</p>
    </div>
  );
}
