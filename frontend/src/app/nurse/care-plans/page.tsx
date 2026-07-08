import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseCarePlansPage() {
  return <EntityDashboard entity="nurse" view="care-plans" title="Care Plans" subtitle="Ongoing care routines, visit history, progress notes, and doctor-approved updates." />;
}
