import { Suspense } from 'react';
import { ModernSignup } from '@/components/auth/ModernSignup';

export default function SignupPage() {
  return <Suspense fallback={<div className="min-h-screen bg-[#f4f5ef]" />}><ModernSignup /></Suspense>;
}
