import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalNotificationsPage() {
  return <EntityDashboard entity="hospital" view="notifications" title="Hospital Notifications" subtitle="Critical queue events, specialist status changes, and system notices." />;
}
