import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function AdminSystemHealthPage() {
  return <EntityDashboard entity="admin" view="vitals" title="System Health" subtitle="Real-time service status" />;
}
