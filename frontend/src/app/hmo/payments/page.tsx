import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoPaymentsPage() {
  return <EntityDashboard entity="hmo" view="payments" title="Payments" subtitle="Outgoing facility payments, incoming premiums, wallet balance, and batch processing." />;
}
