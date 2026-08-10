import Link from 'next/link';
import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function AdminOverviewPage() {
  return <><EntityDashboard entity="admin" view="overview" title="Platform Overview" subtitle="ClinicalFlow system dashboard" /><div className="px-6 pb-10"><Link href="/dashboard/admin/enterprise-enquiries" className="inline-flex rounded-xl border border-slate-200 bg-white px-5 py-3 font-semibold text-[#0b5d4b]">Enterprise enquiries</Link></div></>;
}
