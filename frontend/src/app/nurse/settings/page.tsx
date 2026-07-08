import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseSettingsPage() {
  return <EntityDashboard entity="nurse" view="settings" title="Nurse Settings" subtitle="Role mode, NMCN details, service types, availability, and notification preferences." />;
}
