import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoNotificationsPage() {
  return <EntityDashboard entity="hmo" view="notifications" title="HMO Notifications" subtitle="Authorization requests, claims events, utilization alerts, and facility updates." />;
}
