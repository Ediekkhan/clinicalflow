import {
  BarChart2,
  Bell,
  Building,
  Calendar,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileText,
  FlaskConical,
  Heart,
  Home,
  LayoutDashboard,
  LayoutGrid,
  MapPin,
  MessageSquare,
  Package,
  Settings,
  Stethoscope,
  Ticket,
  Users,
} from 'lucide-react';
import type { DashboardNavItem } from '@/components/layout/MobileBottomNav';

export type EntityKey = 'patient' | 'specialist' | 'hospital' | 'clinic' | 'pharmacy' | 'lab' | 'nurse' | 'hmo' | 'moh' | 'admin';

export type DashboardEntity = {
  entityType: string;
  basePath: string;
  identity: {
    name: string;
    subtitle: string;
    badge?: string;
    initials: string;
  };
  nav: DashboardNavItem[];
  stats: never[];
  activity: never[];
  queue: never[];
  table: {
    columns: string[];
    rows: never[];
  };
};

const patientNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/dashboard', icon: Home },
  { label: 'AI Triage', href: '/dashboard/chat', icon: MessageSquare },
  { label: 'Appointments', href: '/dashboard/appointments', icon: Calendar },
  { label: 'My Visit', href: '/my-visit', icon: Ticket },
  { label: 'My Card', href: '/dashboard/card', icon: CreditCard },
  { label: 'Health History', href: '/dashboard/history', icon: FileText },
  { label: 'Settings', href: '/dashboard/settings', icon: Settings },
];

const specialistNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/specialist/dashboard', icon: LayoutDashboard },
  { label: 'Patient Queue', href: '/specialist/patients', icon: Users },
  { label: 'Appointments', href: '/specialist/appointments', icon: Calendar },
  { label: 'Patient Records', href: '/specialist/notes', icon: FileText },
  { label: 'Schedule', href: '/specialist/schedule', icon: Calendar },
  { label: 'Analytics', href: '/specialist/earnings', icon: BarChart2 },
  { label: 'Settings', href: '/specialist/settings', icon: Settings },
];

const hospitalNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/hospital/dashboard', icon: LayoutDashboard },
  { label: 'Patient Queue', href: '/hospital/queue', icon: Users },
  { label: 'Specialists', href: '/hospital/specialists', icon: Stethoscope },
  { label: 'Appointments', href: '/hospital/appointments', icon: Calendar },
  { label: 'Departments', href: '/hospital/departments', icon: Building },
  { label: 'Analytics', href: '/hospital/analytics', icon: BarChart2 },
  { label: 'Notifications', href: '/hospital/notifications', icon: Bell },
  { label: 'Settings', href: '/hospital/settings', icon: Settings },
];

const clinicNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/clinic/dashboard', icon: LayoutDashboard },
  { label: 'Patient Queue', href: '/clinic/queue', icon: Users },
  { label: 'Doctors', href: '/clinic/doctors', icon: Stethoscope },
  { label: 'Appointments', href: '/clinic/appointments', icon: Calendar },
  { label: 'Analytics', href: '/clinic/analytics', icon: BarChart2 },
  { label: 'Notifications', href: '/clinic/notifications', icon: Bell },
  { label: 'Settings', href: '/clinic/settings', icon: Settings },
];

const pharmacyNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/pharmacy/dashboard', icon: LayoutDashboard },
  { label: 'Prescriptions', href: '/pharmacy/prescriptions', icon: ClipboardList },
  { label: 'Inventory', href: '/pharmacy/inventory', icon: Package },
  { label: 'Dispensed Log', href: '/pharmacy/dispensed-log', icon: ClipboardCheck },
  { label: 'Settings', href: '/pharmacy/settings', icon: Settings },
];

const labNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/lab/dashboard', icon: LayoutDashboard },
  { label: 'Test Requests', href: '/lab/requests', icon: FlaskConical },
  { label: 'Results', href: '/lab/results', icon: ClipboardCheck },
  { label: 'Equipment', href: '/lab/equipment', icon: LayoutGrid },
  { label: 'Settings', href: '/lab/settings', icon: Settings },
];

const nurseNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/nurse/dashboard', icon: LayoutDashboard },
  { label: 'Triage Queue', href: '/nurse/queue', icon: Users },
  { label: 'Home Visits', href: '/nurse/visits', icon: MapPin },
  { label: 'My Patients', href: '/nurse/patients', icon: Users },
  { label: 'Schedule', href: '/nurse/schedule', icon: Calendar },
  { label: 'Vitals Entry', href: '/nurse/vitals', icon: Heart },
  { label: 'Care Plans', href: '/nurse/care-plans', icon: Heart },
  { label: 'Notifications', href: '/nurse/notifications', icon: Bell },
  { label: 'Settings', href: '/nurse/settings', icon: Settings },
];

const hmoNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/hmo/dashboard', icon: LayoutDashboard },
  { label: 'Claims', href: '/hmo/claims', icon: FileText },
  { label: 'Members', href: '/hmo/members', icon: Users },
  { label: 'Analytics', href: '/hmo/analytics', icon: BarChart2 },
  { label: 'Settings', href: '/hmo/settings', icon: Settings },
];

const mohNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/moh/dashboard', icon: LayoutDashboard },
  { label: 'State Reports', href: '/moh/reports', icon: FileText },
  { label: 'Hospitals', href: '/moh/hospitals', icon: Building },
  { label: 'Surveillance', href: '/moh/surveillance', icon: Heart },
  { label: 'Settings', href: '/moh/settings', icon: Settings },
];

const adminNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/dashboard/admin', icon: LayoutDashboard },
  { label: 'Users', href: '/dashboard/admin/users', icon: Users },
  { label: 'Hospitals', href: '/dashboard/admin/hospitals', icon: Building },
  { label: 'Audit Log', href: '/dashboard/admin/audit-log', icon: FileText },
  { label: 'System Health', href: '/dashboard/admin/system-health', icon: LayoutGrid },
  { label: 'Settings', href: '/dashboard/admin/settings', icon: Settings },
];

function emptyEntity(entityType: string, basePath: string, nav: DashboardNavItem[], initials: string, subtitle = 'Secure workspace'): DashboardEntity {
  return {
    entityType,
    basePath,
    identity: { name: entityType, subtitle, initials },
    nav,
    stats: [],
    activity: [],
    queue: [],
    table: { columns: [], rows: [] },
  };
}

export const dashboardEntities: Record<EntityKey, DashboardEntity> = {
  patient: emptyEntity('Patient', '/dashboard', patientNav, 'PT', 'Patient portal'),
  specialist: emptyEntity('Doctor / Specialist', '/specialist/dashboard', specialistNav, 'SP', 'Specialist portal'),
  hospital: emptyEntity('Hospital', '/hospital/dashboard', hospitalNav, 'HO', 'Facility portal'),
  clinic: emptyEntity('Clinic', '/clinic/dashboard', clinicNav, 'CL', 'Clinic portal'),
  pharmacy: emptyEntity('Pharmacy', '/pharmacy/dashboard', pharmacyNav, 'PH', 'Pharmacy portal'),
  lab: emptyEntity('Laboratory', '/lab/dashboard', labNav, 'LB', 'Laboratory portal'),
  nurse: emptyEntity('Nurse', '/nurse/dashboard', nurseNav, 'NS', 'Nurse portal'),
  hmo: emptyEntity('HMO / Health Insurance', '/hmo/dashboard', hmoNav, 'HM', 'Insurance portal'),
  moh: emptyEntity('State Ministry of Health', '/moh/dashboard', mohNav, 'MH', 'Government portal'),
  admin: emptyEntity('Admin', '/dashboard/admin', adminNav, 'AD', 'Administration'),
};

export const conditionRows: string[][] = [];
export const signupEntities: string[] = [];
