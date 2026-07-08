import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalSettingsPage() {
  return <EntityDashboard entity="hospital" view="settings" title="Hospital Settings" subtitle="Manage tenant profile, routing rules, notifications, departments, and staff access." />;
}
