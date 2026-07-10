import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalSchedulePage() {
  return <EntityDashboard entity="hospital" view="schedule" title="Hospital Schedule" subtitle="Provider availability and appointments from the API." />;
}
