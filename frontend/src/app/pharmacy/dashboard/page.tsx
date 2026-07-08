import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyDashboardPage() {
  return <EntityDashboard entity="pharmacy" view="overview" title="Pharmacy Overview" subtitle="Incoming prescriptions, fulfillment status, deliveries, and low-stock alerts." />;
}
