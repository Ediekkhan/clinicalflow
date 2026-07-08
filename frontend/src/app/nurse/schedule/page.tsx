import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseSchedulePage() {
  return <EntityDashboard entity="nurse" view="schedule" title="Schedule" subtitle="Shift calendar, patient checks, home visits, and care plan follow-ups." />;
}
