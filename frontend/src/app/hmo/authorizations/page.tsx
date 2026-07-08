import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoAuthorizationsPage() {
  return <EntityDashboard entity="hmo" view="authorizations" title="Authorizations" subtitle="Approve, decline, or request more information for incoming care authorization requests." />;
}
