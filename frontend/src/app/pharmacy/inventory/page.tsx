import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyInventoryPage() {
  return <EntityDashboard entity="pharmacy" view="inventory" title="Inventory" subtitle="Stock counts, reorder levels, low-stock flags, and controlled substance filters." />;
}
