import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicNotificationsPage() {
  return <EntityDashboard entity="clinic" view="notifications" title="Clinic Notifications" subtitle="Queue changes, appointment updates, and patient arrival alerts." />;
}
