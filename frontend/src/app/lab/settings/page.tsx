import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabSettingsPage() {
  return <EntityDashboard entity="lab" view="settings" title="Lab Settings" subtitle="Collection methods, result templates, technician access, and notification rules." />;
}
