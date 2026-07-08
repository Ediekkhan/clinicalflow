import {
  BarChart2,
  Bell,
  Building,
  Building2,
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
  Pill,
  Settings,
  Shield,
  Stethoscope,
  Ticket,
  Users,
  Wallet,
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
  stats: { title: string; value: string; sub: string; tone: 'amber' | 'rose' | 'sky' | 'slate' | 'violet'; href?: string }[];
  activity: string[];
  queue: {
    ticket: string;
    patient: string;
    condition: string;
    urgency: 'CRITICAL' | 'URGENT' | 'ROUTINE';
    status: 'QUEUED' | 'BEING_SEEN' | 'RESOLVED';
    meta: string;
  }[];
  table: {
    columns: string[];
    rows: (string | number)[][];
  };
};

const patientNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/dashboard', icon: Home },
  { label: 'AI Triage', href: '/dashboard/chat', icon: MessageSquare },
  { label: 'Appointments', href: '/dashboard/appointments', icon: Calendar },
  { label: 'My Queue', href: '/dashboard/queue', icon: Ticket },
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

const adminNav: DashboardNavItem[] = [
  { label: 'Overview', href: '/dashboard/admin', icon: LayoutDashboard },
  { label: 'Users', href: '/dashboard/admin/users', icon: Users },
  { label: 'Hospitals', href: '/dashboard/admin/hospitals', icon: Building },
  { label: 'Audit Log', href: '/dashboard/admin/audit-log', icon: FileText },
  { label: 'System Health', href: '/dashboard/admin/system-health', icon: LayoutGrid },
  { label: 'Settings', href: '/dashboard/admin/settings', icon: Settings },
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

export const dashboardEntities: Record<EntityKey, DashboardEntity> = {
  patient: {
    entityType: 'Patient',
    basePath: '/dashboard',
    identity: {
      name: 'Hello, Adaeze',
      subtitle: 'Patient portal',
      badge: 'SV-AKS-2026-00412',
      initials: 'AC',
    },
    nav: patientNav,
    stats: [
      { title: 'Active Tickets', value: '1', sub: 'URGENT - Cardiologist', tone: 'amber', href: '/dashboard/queue' },
      { title: 'Next Appointment', value: 'Today 3:00 PM', sub: 'Dr. Okon - Cardiology', tone: 'sky', href: '/dashboard/appointments' },
      { title: 'Queue Position', value: '#3', sub: 'Pulsing live queue', tone: 'sky', href: '/dashboard/queue' },
      { title: 'Health Card', value: 'SV-AKS', sub: 'Digital card ready', tone: 'slate', href: '/dashboard/card' },
    ],
    activity: [
      'AI triage completed - Urgent - 2h ago',
      'Appointment confirmed - Today 3:00 PM - 2h ago',
      'Ticket SV-2026-00412 created - 2h ago',
      'Health card refreshed - yesterday',
      'Queue position changed from #4 to #3',
    ],
    queue: [
      {
        ticket: 'SV-AKS-2026-00412',
        patient: 'Adaeze Chukwu',
        condition: 'Possible hypertensive crisis',
        urgency: 'URGENT',
        status: 'QUEUED',
        meta: 'Cardiologist - Room 4 - Ibom Specialist Hospital',
      },
    ],
    table: {
      columns: ['Date', 'Event', 'Specialist', 'Status'],
      rows: [
        ['Jun 19', 'AI triage', 'Dr. Effiong', 'URGENT'],
        ['Jun 19', 'Appointment', 'Dr. Okon', 'BOOKED'],
        ['Jun 12', 'Routine follow-up', 'Dr. Udo', 'COMPLETE'],
      ],
    },
  },
  specialist: {
    entityType: 'Doctor / Specialist',
    basePath: '/specialist/dashboard',
    identity: { name: 'Dr. Okon Bassey', subtitle: 'Cardiologist · ISH', initials: 'OB' },
    nav: specialistNav,
    stats: [
      { title: "Today's Appointments", value: '8', sub: '+2 from yesterday', tone: 'slate' },
      { title: 'Waiting Now', value: '3', sub: '3 waiting', tone: 'amber', href: '/specialist/patients' },
      { title: 'Resolved Today', value: '5', sub: '5 of 8 complete', tone: 'sky', href: '/specialist/patients?status=resolved' },
      { title: "This Month's Earnings", value: '₦127,500', sub: '₦45,000 pending payout', tone: 'violet' },
    ],
    activity: [
      'Adaeze Chukwu assigned to you - 4 min ago',
      'Ticket SV-AKS-2026-00498 escalated by nurse',
      'Prescription sent to MedPlus Pharmacy',
      'Schedule reminder - Emeka Obi starts in 15 min',
    ],
    queue: [
      { ticket: 'SV-AKS-2026-00412', patient: 'Adaeze Chukwu', condition: 'Hypertensive Crisis', urgency: 'URGENT', status: 'QUEUED', meta: 'Waiting 12 min' },
      { ticket: 'SV-AKS-2026-00498', patient: 'Fatima Hassan', condition: 'Chest Pain', urgency: 'CRITICAL', status: 'BEING_SEEN', meta: 'Session 00:14:32' },
      { ticket: 'SV-AKS-2026-00521', patient: 'Emeka Obi', condition: 'Arrhythmia review', urgency: 'ROUTINE', status: 'RESOLVED', meta: 'Resolved 2h ago' },
    ],
    table: {
      columns: ['Date', 'Patient', 'Ticket', 'Fee', 'Status'],
      rows: [
        ['Jun 19', 'Adaeze Chukwu', 'SV-00412', '₦15,000', 'PENDING'],
        ['Jun 18', 'Emeka Obi', 'SV-00521', '₦15,000', 'PAID'],
        ['Jun 17', 'Fatima Hassan', 'SV-00498', '₦25,000', 'PAID'],
      ],
    },
  },
  hospital: {
    entityType: 'Hospital',
    basePath: '/hospital/dashboard',
    identity: { name: 'Ibom Specialist Hospital', subtitle: 'Akwa Ibom - Uyo', initials: 'IH' },
    nav: hospitalNav,
    stats: [
      { title: 'Total Patients Today', value: '47', sub: '+12 from yesterday', tone: 'sky', href: '/hospital/queue' },
      { title: 'Currently Being Seen', value: '8', sub: 'In consultation', tone: 'sky', href: '/hospital/queue?status=being-seen' },
      { title: 'Waiting in Queue', value: '23', sub: 'Amber load', tone: 'amber', href: '/hospital/queue?status=waiting' },
      { title: 'Available Specialists', value: '12/18', sub: 'Coverage 67%', tone: 'sky', href: '/hospital/specialists' },
      { title: 'Appointments Today', value: '34', sub: 'Scheduled', tone: 'slate', href: '/hospital/appointments' },
      { title: 'Average Wait Time', value: '38m', sub: '-5 min from last week', tone: 'violet', href: '/hospital/analytics' },
    ],
    activity: [
      'Critical cardiology ticket accepted',
      'Emergency department queue crossed 70%',
      'Dr. Ada Balogun marked unavailable',
      '34 appointments confirmed for today',
    ],
    queue: [
      { ticket: 'SV-AKS-2026-00412', patient: 'Adaeze Chukwu', condition: 'Cardiology', urgency: 'URGENT', status: 'QUEUED', meta: 'Room 4 - Nurse Ini' },
      { ticket: 'SV-AKS-2026-00498', patient: 'Fatima Hassan', condition: 'Emergency', urgency: 'CRITICAL', status: 'BEING_SEEN', meta: 'Room ER-1 - Dr. Udo' },
      { ticket: 'SV-AKS-2026-00521', patient: 'Emeka Obi', condition: 'General', urgency: 'ROUTINE', status: 'QUEUED', meta: 'Room 2 - Nurse Grace' },
    ],
    table: {
      columns: ['Department', 'Waiting', 'Doctors', 'Fill', 'Status'],
      rows: [
        ['Emergency', 7, '3 of 4', '82%', 'HIGH'],
        ['Cardiology', 4, '2 of 3', '55%', 'ACTIVE'],
        ['Pediatrics', 3, '2 of 2', '35%', 'NORMAL'],
        ['OB-GYN', 5, '1 of 2', '66%', 'ACTIVE'],
      ],
    },
  },
  clinic: {
    entityType: 'Clinic',
    basePath: '/clinic/dashboard',
    identity: { name: 'Meridian Clinic Eket', subtitle: 'Clinic Admin', initials: 'MC' },
    nav: clinicNav,
    stats: [
      { title: 'Patients Today', value: '18', sub: '+4 from yesterday', tone: 'sky', href: '/clinic/queue' },
      { title: 'Waiting', value: '9', sub: 'Single clinic queue', tone: 'amber', href: '/clinic/queue' },
      { title: 'Available Doctors', value: '3/4', sub: 'One unavailable', tone: 'sky', href: '/clinic/doctors' },
      { title: 'Appointments', value: '12', sub: 'Next five listed below', tone: 'slate', href: '/clinic/appointments' },
    ],
    activity: ['Walk-in ticket created', 'Vitals saved for SV-00412', 'Dr. Udo accepted assignment', 'Clinic profile viewed by patient'],
    queue: [
      { ticket: 'SV-AKS-2026-00444', patient: 'Blessing Udofia', condition: 'Malaria', urgency: 'ROUTINE', status: 'QUEUED', meta: 'General - Room 2' },
      { ticket: 'SV-AKS-2026-00445', patient: 'Victor Ekanem', condition: 'UTI', urgency: 'URGENT', status: 'BEING_SEEN', meta: 'Dr. Udo' },
    ],
    table: {
      columns: ['Doctor', 'Specialty', 'Status', 'Patients', 'Status'],
      rows: [
        ['Dr. Udo Okon', 'General Practice', 'Available', 7, 'ACTIVE'],
        ['Dr. Ekanem', 'Pediatrics', 'Available', 5, 'ACTIVE'],
        ['Dr. Ada', 'Cardiology', 'Unavailable', 0, 'OFF'],
      ],
    },
  },
  pharmacy: {
    entityType: 'Pharmacy',
    basePath: '/pharmacy/dashboard',
    identity: { name: 'Central Pharmacy', subtitle: 'Ibom Specialist Hospital', initials: 'CP' },
    nav: pharmacyNav,
    stats: [
      { title: 'Pending Prescriptions', value: '7', sub: 'To fill', tone: 'amber', href: '/pharmacy/prescriptions' },
      { title: 'Fulfilled Today', value: '23', sub: 'Ready and dispensed', tone: 'sky', href: '/pharmacy/dispensed-log' },
      { title: 'Delivery Orders', value: '4', sub: 'Pending pickup', tone: 'sky', href: '/pharmacy/prescriptions?status=delivery' },
      { title: 'Low Stock Alerts', value: '3', sub: 'Review inventory', tone: 'rose', href: '/pharmacy/inventory?status=low' },
    ],
    activity: ['Artemether/Lumefantrine prescription accepted', 'ORS sachets marked low stock', 'Patient notified prescription is ready', 'Delivery assigned to rider'],
    queue: [
      { ticket: 'RX-2026-7742', patient: 'A. Chukwu', condition: 'Artemether/Lumefantrine x6', urgency: 'URGENT', status: 'QUEUED', meta: 'Dr. Effiong - Ibom Specialist' },
      { ticket: 'RX-2026-7743', patient: 'E. Obi', condition: 'Paracetamol 500mg x10', urgency: 'ROUTINE', status: 'BEING_SEEN', meta: 'Being prepared' },
    ],
    table: {
      columns: ['Drug Name', 'Category', 'Stock Qty', 'Reorder Level', 'Status'],
      rows: [
        ['Artemether/Lumefantrine 80/480mg', 'Antimalarial', 42, 20, 'IN STOCK'],
        ['ORS Sachets', 'Rehydration', 8, 15, 'LOW STOCK'],
        ['Metronidazole 400mg', 'Antibiotic', 0, 12, 'OUT'],
      ],
    },
  },
  lab: {
    entityType: 'Laboratory',
    basePath: '/lab/dashboard',
    identity: { name: 'Diagnostic Laboratory', subtitle: 'Ibom Specialist Hospital', initials: 'LT' },
    nav: labNav,
    stats: [
      { title: 'Pending Test Requests', value: '12', sub: 'Samples to process', tone: 'amber', href: '/lab/requests?status=pending' },
      { title: 'Awaiting Collection', value: '5', sub: '3 home pickups', tone: 'sky', href: '/lab/requests?status=awaiting-collection' },
      { title: 'Results Ready', value: '8', sub: 'To release', tone: 'sky', href: '/lab/results' },
      { title: 'Completed Today', value: '34', sub: 'Tests completed', tone: 'slate', href: '/lab/results?status=today' },
      { title: 'Turnaround Time', value: '4.2h', sub: 'Average today', tone: 'violet', href: '/lab/analytics' },
    ],
    activity: ['Full Blood Count referral accepted', 'Malaria RDT uploaded', 'Critical abnormal value flagged', 'Collection officer assigned'],
    queue: [
      { ticket: 'LAB-2026-4421', patient: 'F. Ekwueme', condition: 'FBC + Malaria RDT', urgency: 'URGENT', status: 'QUEUED', meta: 'Walk-in collection' },
      { ticket: 'LAB-2026-4422', patient: 'B. Udofia', condition: 'Liver Function Tests', urgency: 'ROUTINE', status: 'BEING_SEEN', meta: 'In processing' },
    ],
    table: {
      columns: ['Request', 'Tests', 'Stage', 'Technician', 'Status'],
      rows: [
        ['LAB-4421', 'FBC, Malaria RDT', 'Sample Collection', 'Mfon', 'ACTIVE'],
        ['LAB-4422', 'LFT', 'Results Ready', 'Joy', 'READY'],
        ['LAB-4423', 'RBS', 'Released', 'Timi', 'COMPLETE'],
      ],
    },
  },
  nurse: {
    entityType: 'Nurse',
    basePath: '/nurse/dashboard',
    identity: { name: 'Nurse Blessing Effiong', subtitle: 'Community Nurse · Uyo', initials: 'BE' },
    nav: nurseNav,
    stats: [
      { title: 'Patients in Queue', value: '14', sub: 'Clinic floor', tone: 'amber', href: '/nurse/queue' },
      { title: 'Critical Cases', value: '2', sub: 'Needs immediate review', tone: 'rose', href: '/nurse/patients?status=critical' },
      { title: 'Being Seen Now', value: '6', sub: 'In consultation', tone: 'sky', href: '/nurse/queue?status=being-seen' },
      { title: 'Waiting > 45min', value: '3', sub: 'Escalation watch', tone: 'amber', href: '/nurse/queue?status=delayed' },
    ],
    activity: ['Vitals saved for Adaeze Chukwu', 'BP 190/112 escalated automatically', 'Home visit report submitted', 'Queue overtake confirmed'],
    queue: [
      { ticket: 'SV-AKS-2026-00412', patient: 'Adaeze Chukwu', condition: 'High BP vitals', urgency: 'CRITICAL', status: 'QUEUED', meta: 'Record vitals - Room 4' },
      { ticket: 'SV-AKS-2026-00444', patient: 'Blessing Udofia', condition: 'Fever review', urgency: 'ROUTINE', status: 'BEING_SEEN', meta: 'Checked in' },
    ],
    table: {
      columns: ['Patient', 'Temperature', 'BP', 'SpO2', 'Status'],
      rows: [
        ['Adaeze Chukwu', '38.8 C', '190/112', '94%', 'ESCALATED'],
        ['Emeka Obi', '37.1 C', '124/82', '98%', 'NORMAL'],
        ['Fatima Hassan', '39.6 C', '130/88', '96%', 'URGENT'],
      ],
    },
  },
  hmo: {
    entityType: 'HMO / Health Insurance',
    basePath: '/hmo/dashboard',
    identity: { name: 'HealthBridge HMO', subtitle: 'Partner Provider', initials: 'HMO' },
    nav: hmoNav,
    stats: [
      { title: 'Total Enrollees', value: '4,820', sub: 'Active plan', tone: 'slate', href: '/hmo/members' },
      { title: 'Active This Month', value: '1,247', sub: '25.8% utilization', tone: 'sky', href: '/hmo/members?status=active' },
      { title: 'Pending Authorizations', value: '34', sub: 'Awaiting approval', tone: 'amber', href: '/hmo/claims?status=pending' },
      { title: 'Claims This Month', value: '₦12.4M', sub: 'vs ₦10.1M last month', tone: 'violet', href: '/hmo/claims' },
      { title: 'Approved Claims', value: '₦9.8M', sub: '78.9% approval', tone: 'sky', href: '/hmo/claims?status=approved' },
      { title: 'Partner Facilities', value: '67', sub: '47 clinics, 8 labs, 12 pharmacies', tone: 'sky', href: '/hmo/facilities' },
    ],
    activity: ['AUTH-2026-84712 approved', 'Malaria treatment request submitted', 'Claim batch marked under review', 'Facility rating refreshed'],
    queue: [
      { ticket: 'AUTH-2026-84712', patient: 'Adaeze Chukwu', condition: 'Consultation - Malaria treatment', urgency: 'URGENT', status: 'QUEUED', meta: 'Estimated ₦15,000 - Uyo Family Clinic' },
      { ticket: 'AUTH-2026-84713', patient: 'Emeka Obi', condition: 'Cardiology review', urgency: 'CRITICAL', status: 'QUEUED', meta: 'Pinned critical case' },
    ],
    table: {
      columns: ['Facility', 'Claims Paid', 'Amount', 'Date', 'Status'],
      rows: [
        ['Uyo Family Clinic', 42, '₦1.8M', 'Jun 19', 'PROCESSING'],
        ['Prime Diagnostics', 18, '₦720K', 'Jun 18', 'PAID'],
        ['MedPlus Pharmacy', 31, '₦980K', 'Jun 17', 'PENDING'],
      ],
    },
  },
  moh: {
    entityType: 'State Ministry of Health',
    basePath: '/moh/dashboard',
    identity: { name: 'Akwa Ibom MoH', subtitle: 'Ministry of Health', initials: 'AK' },
    nav: mohNav,
    stats: [
      { title: 'Registered Facilities', value: '156', sub: '23 SynaptiVerse partners', tone: 'slate', href: '/moh/hospitals' },
      { title: 'Patient Encounters', value: '42,819', sub: 'This month across all LGAs', tone: 'slate', href: '/moh/reports' },
      { title: 'AI Triage Sessions', value: '18,234', sub: '72% of total encounters', tone: 'sky', href: '/moh/reports?metric=ai-triage' },
      { title: 'Active Health Alerts', value: '2', sub: 'Malaria · UTI uptick', tone: 'rose', href: '/moh/surveillance?status=active' },
    ],
    activity: [],
    queue: [],
    table: {
      columns: ['LGA', 'Facilities', 'Patient Volume', 'Top Condition', 'AI Triage %'],
      rows: [
        ['Uyo', 34, '12,450', 'Hypertension', '74%'],
        ['Eket', 18, '6,820', 'Malaria', '68%'],
        ['Ikot Ekpene', 22, '7,340', 'Malaria', '71%'],
      ],
    },
  },
  admin: {
    entityType: 'Admin',
    basePath: '/dashboard/admin',
    identity: { name: 'System Administrator', subtitle: 'SynaptiVerse Core', initials: 'SA' },
    nav: adminNav,
    stats: [
      { title: 'Total Users', value: '12,847', sub: '+234 this week', tone: 'slate', href: '/dashboard/admin/users' },
      { title: 'Active Hospitals', value: '23', sub: '2 pending approval', tone: 'slate', href: '/dashboard/admin/hospitals' },
      { title: 'Tickets Today', value: '1,204', sub: 'Across all facilities', tone: 'slate', href: '/dashboard/admin/audit-log' },
      { title: 'System Uptime', value: '99.97%', sub: '30-day average', tone: 'sky', href: '/dashboard/admin/system-health' },
    ],
    activity: [
      'New hospital registered: Meridian Clinic Eket',
      'User suspended: john.doe@example.com',
      'AI service latency spike (1.8s avg)',
      'Scheduled backup completed',
      'System update deployed: v2.1.4',
    ],
    queue: [
      { ticket: 'SYS-001', patient: 'API Server', condition: 'Operational', urgency: 'ROUTINE', status: 'RESOLVED', meta: '99.97% uptime' },
    ],
    table: {
      columns: ['Name', 'Role', 'Status', 'Joined', 'Actions'],
      rows: [
        ['Adaeze Chukwu', 'Patient', 'Active', 'Jun 20, 2026', 'View'],
        ['Dr. Okon Bassey', 'Doctor', 'Active', 'Jan 15, 2026', 'View'],
        ['Ibom Specialist Hospital', 'Hospital', 'Active', 'Mar 1, 2026', 'View'],
        ['John Doe', 'Patient', 'Suspended', 'May 5, 2026', 'Restore'],
      ],
    },
  },
};

export const conditionRows = [
  ['Heart Attack', 'Stroke', 'Hypertensive Crisis', 'Chest Pain', 'Severe Malaria', 'Cerebral Malaria', 'Preeclampsia', 'Eclampsia', 'Sickle Cell Crisis', 'DKA', 'Meningitis', 'Sepsis', 'Appendicitis', 'Anaphylaxis', 'Snakebite', 'Severe Burns'],
  ['Malaria', 'Typhoid Fever', 'Pneumonia', 'Asthma', 'UTI', 'Diabetes', 'Hypertension', 'Peptic Ulcer', 'Low Back Pain', 'Conjunctivitis', 'Ear Infection', 'Skin Rash', 'Anxiety', 'Depression', 'Kidney Stones', 'GERD', 'IBS'],
];

export const signupEntities = [
  { type: 'patient', label: 'Patient', description: 'Check symptoms & book appointments', icon: Users, tone: 'sky' },
  { type: 'specialist', label: 'Doctor / Specialist', description: 'Join our specialist network', icon: Stethoscope, tone: 'sky' },
  { type: 'hospital', label: 'Hospital', description: 'Enterprise multi-department setup', icon: Building, tone: 'blue' },
  { type: 'clinic', label: 'Clinic', description: 'Private or specialist clinic', icon: Building2, tone: 'violet' },
  { type: 'pharmacy', label: 'Pharmacy', description: 'Join the prescription network', icon: Pill, tone: 'amber' },
  { type: 'lab', label: 'Laboratory', description: 'Diagnostic & imaging centre', icon: FlaskConical, tone: 'rose' },
  { type: 'nurse', label: 'Nurse', description: 'Community & clinical nursing', icon: Heart, tone: 'pink' },
  { type: 'hmo', label: 'HMO / Health Insurance', description: 'Manage enrollees & providers', icon: Shield, tone: 'indigo' },
];
