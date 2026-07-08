import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoSettingsPage() {
  return <EntityDashboard entity="hmo" view="settings" title="HMO Settings" subtitle="Organization profile, NHIS details, claims policies, and integration preferences." />;
}
