import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicAppointmentsPage() {
  return <EntityDashboard entity="clinic" view="appointments" title="Clinic Appointments" subtitle="Today’s appointments, walk-ins, and follow-up slots." />;
}
