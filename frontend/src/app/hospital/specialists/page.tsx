import { HospitalRecordsPage } from '@/components/HospitalRecordsPage';
import { HospitalShell } from '@/components/HospitalShell';

export default function HospitalSpecialistsPage() {
  return (
    <HospitalShell>
      <HospitalRecordsPage mode="specialists" title="Specialists" subtitle="Verified doctors and specialists working in this hospital workspace." />
    </HospitalShell>
  );
}
