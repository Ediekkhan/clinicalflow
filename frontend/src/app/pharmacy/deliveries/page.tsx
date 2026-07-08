import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyDeliveriesPage() {
  return <EntityDashboard entity="pharmacy" view="deliveries" title="Deliveries" subtitle="Pickup and delivery orders with rider assignment and status transitions." />;
}
