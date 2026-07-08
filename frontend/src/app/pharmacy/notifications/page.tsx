import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyNotificationsPage() {
  return <EntityDashboard entity="pharmacy" view="notifications" title="Pharmacy Notifications" subtitle="Prescription routing, refill alerts, inventory warnings, and pickup updates." />;
}
