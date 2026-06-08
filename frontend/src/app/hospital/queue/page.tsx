'use client';

import { HospitalShell } from '@/components/HospitalShell';
import { NetworkToast } from '@/components/NetworkToast';
import { TriageKanban } from '@/components/TriageKanban';
import { useTriageQueue } from '@/hooks/useTriageQueue';

export default function HospitalQueuePage() {
  const { grouped, networkMode, forceOvertake, setStatus } = useTriageQueue();

  return (
    <HospitalShell>
      <NetworkToast mode={networkMode} />
      <main className="mx-auto max-w-7xl p-4 md:p-6">
        <div className="mb-5">
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Hospital Live Queue</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">All clinic triage lanes</h1>
        </div>
        <TriageKanban grouped={grouped} forceOvertake={forceOvertake} setStatus={setStatus} />
      </main>
    </HospitalShell>
  );
}
