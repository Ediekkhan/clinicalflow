import { notFound } from 'next/navigation';
import { AuthFrame } from '@/components/auth/AuthFrame';
import { RoleSignupForm } from '@/components/auth/RoleSignupForm';
import { signupConfigs, type SignupRole } from '@/lib/signup-config';

export function generateStaticParams() {
  return Object.keys(signupConfigs).map((role) => ({ role }));
}

export default async function RoleSignupPage({ params }: { params: Promise<{ role: string }> }) {
  const { role } = await params;
  const config = signupConfigs[role as SignupRole];
  if (!config) notFound();
  return (
    <AuthFrame eyebrow={`${config.name} onboarding`} title={`Apply for the ${config.name} workspace.`} description={config.description}>
      <RoleSignupForm config={config} />
    </AuthFrame>
  );
}