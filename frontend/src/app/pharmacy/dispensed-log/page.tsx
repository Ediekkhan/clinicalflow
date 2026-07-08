import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyDispensedLogPage() {
  return <EntityDashboard entity="pharmacy" view="deliveries" title="Dispensed Log" subtitle="Today · 34 prescriptions dispensed" />;
}
