import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicDoctorsPage() {
  return <EntityDashboard entity="clinic" view="people" title="My Specialists" subtitle="Manage doctors, availability, schedules, and patient load for this clinic." />;
}
