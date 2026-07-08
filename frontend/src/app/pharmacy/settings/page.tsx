import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacySettingsPage() {
  return <EntityDashboard entity="pharmacy" view="settings" title="Pharmacy Settings" subtitle="Delivery settings, operating hours, stock notification rules, and network profile." />;
}
