import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseNotificationsPage() {
  return <EntityDashboard entity="nurse" view="notifications" title="Nurse Notifications" subtitle="Vitals alerts, queue events, home visit reminders, and doctor messages." />;
}
