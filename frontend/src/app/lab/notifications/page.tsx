import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabNotificationsPage() {
  return <EntityDashboard entity="lab" view="notifications" title="Lab Notifications" subtitle="New test referrals, abnormal results, release confirmations, and pickup updates." />;
}
