import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function AdminUsersPage() {
  return <EntityDashboard entity="admin" view="people" title="Users" subtitle="Registered users from the API" />;
}
