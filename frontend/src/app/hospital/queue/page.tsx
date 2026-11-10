import { HospitalRecordsPage } from '@/components/HospitalRecordsPage';
import { HospitalShell } from '@/components/HospitalShell';

export default function HospitalQueuePage() {
  return (
    <HospitalShell>
      <HospitalRecordsPage mode="queue" title="Hospital Patient Queue" subtitle="Patients routed or appointed to this hospital, grouped by urgency, assignment and queue state." />
    </HospitalShell>
  );
}
