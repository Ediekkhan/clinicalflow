import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function AdminOverviewPage() {
  return <EntityDashboard entity="admin" view="overview" title="Platform Overview" subtitle="ClinicalFlow system dashboard" />;
}
