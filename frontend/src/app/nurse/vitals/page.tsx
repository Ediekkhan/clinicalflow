import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseVitalsPage() {
  return <EntityDashboard entity="nurse" view="vitals" title="Vitals" subtitle="Record temperature, BP, pulse, SpO2, respiratory rate, weight, height, BMI, and blood sugar." />;
}
