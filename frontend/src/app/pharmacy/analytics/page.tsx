import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyAnalyticsPage() {
  return <EntityDashboard entity="pharmacy" view="analytics" title="Pharmacy Analytics" subtitle="Fulfillment volume, low-stock patterns, and prescription category mix." />;
}
