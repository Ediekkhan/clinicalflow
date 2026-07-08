import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabPatientsPage() {
  return <EntityDashboard entity="lab" view="patients" title="Patients" subtitle="Patient list for referrals, walk-in collections, home pickups, and released result history." />;
}
