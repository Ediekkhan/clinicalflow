import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicSettingsPage() {
  return <EntityDashboard entity="clinic" view="settings" title="Clinic Settings" subtitle="Clinic profile, staff access, notification preferences, and patient-facing details." />;
}
