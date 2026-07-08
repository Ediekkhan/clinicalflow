import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function AdminAuditLogPage() {
  return <EntityDashboard entity="admin" view="messages" title="Audit Log" subtitle="System event history" />;
}
