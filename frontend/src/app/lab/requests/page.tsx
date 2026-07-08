import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabRequestsPage() {
  return <EntityDashboard entity="lab" view="requests" title="Test Requests" subtitle="Incoming referrals, sample collection workflow, processing, upload, and release stages." />;
}
