import { HospitalShell } from '@/components/HospitalShell';
import { NetworkToast } from '@/components/NetworkToast';
import { SpecialistPatientKanban } from '@/components/SpecialistPatientKanban';

export default function HospitalDoctorPatientsPage() {
  return (
    <HospitalShell>
      <NetworkToast mode="connected" />
      <main className="mx-auto grid max-w-7xl gap-5 p-4 md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Doctor View</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">Patients assigned to me</h1>
          <p className="mt-2 text-sm leading-6 text-[#6B7280]">
            This view is scoped to the logged-in doctor inside the hospital account.
          </p>
        </div>
        <SpecialistPatientKanban assignedOnly />
      </main>
    </HospitalShell>
  );
}
