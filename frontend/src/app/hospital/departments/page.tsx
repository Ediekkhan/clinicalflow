import { HospitalRecordsPage } from '@/components/HospitalRecordsPage';
import { HospitalShell } from '@/components/HospitalShell';

export default function HospitalDepartmentsPage() {
  return (
    <HospitalShell>
      <HospitalRecordsPage mode="departments" title="Departments" subtitle="Active hospital departments, staffing, queue load and available doctors." />
    </HospitalShell>
  );
}
