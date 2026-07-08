import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function AdminUsersPage() {
  return <EntityDashboard entity="admin" view="people" title="Users" subtitle="12,847 registered across all roles" />;
}
