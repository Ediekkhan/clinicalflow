import { AppointmentScheduler } from '@/components/AppointmentScheduler';
import { HospitalShell } from '@/components/HospitalShell';

export default function HospitalAppointmentsPage() {
  return (
    <HospitalShell>
      <main className="mx-auto max-w-7xl p-4 md:p-6">
        <AppointmentScheduler />
      </main>
    </HospitalShell>
  );
}
