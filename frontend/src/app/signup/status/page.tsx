import { Suspense } from 'react';
import { SignupStatus } from '@/components/auth/SignupStatus';

export default function SignupStatusPage() {
  return <Suspense fallback={<div className="min-h-screen bg-[#f4f5ef]" />}><SignupStatus /></Suspense>;
}