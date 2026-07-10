import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyDispensedLogPage() {
  return <EntityDashboard entity="pharmacy" view="deliveries" title="Dispensed Log" subtitle="Dispensed prescriptions from the API" />;
}
