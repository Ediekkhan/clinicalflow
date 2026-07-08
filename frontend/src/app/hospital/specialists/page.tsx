import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalSpecialistsPage() {
  return <EntityDashboard entity="hospital" view="people" title="Specialists Management" subtitle="Availability, schedules, patient counts, ratings, and actions for all registered specialists." />;
}
