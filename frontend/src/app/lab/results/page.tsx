import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabResultsPage() {
  return <EntityDashboard entity="lab" view="results" title="Results" subtitle="Upload PDFs, enter structured results, flag abnormal values, and release to doctors and patients." />;
}
