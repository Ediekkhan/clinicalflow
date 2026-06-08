import { PatientCard } from '@/components/PatientCard';
import { PatientShell } from '@/components/PatientShell';
import { demoPatient } from '@/lib/syn-data';

export default function MyCardPage() {
  return (
    <PatientShell>
      <main className="mx-auto grid max-w-xl gap-6 p-4 md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Health Identity</p>
          <h1 className="font-display text-4xl text-[#111827]">Your SynaptiVerse card</h1>
        </div>
        <PatientCard patient={demoPatient} />
      </main>
    </PatientShell>
  );
}

