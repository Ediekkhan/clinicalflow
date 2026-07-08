import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicAnalyticsPage() {
  return <EntityDashboard entity="clinic" view="analytics" title="Clinic Analytics" subtitle="Simple volume, wait-time, and condition trend reporting for smaller teams." />;
}
