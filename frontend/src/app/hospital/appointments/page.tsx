import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalAppointmentsPage() {
  return <EntityDashboard entity="hospital" view="appointments" title="Hospital Appointments" subtitle="Scheduled consultations across departments and specialists." />;
}
