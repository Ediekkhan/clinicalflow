import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoClaimsPage() {
  return <EntityDashboard entity="hmo" view="claims" title="Claims" subtitle="Review supporting documents, approve amounts, reject claims, and request audits." />;
}
