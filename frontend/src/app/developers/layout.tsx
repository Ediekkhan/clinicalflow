import type { Metadata } from 'next';
import { DocsShell } from '@/components/developers/DocsShell';

export const metadata: Metadata = {
  title: 'ClinicalFlow Developer Documentation',
  description: 'Architecture, API reference, setup and deployment guidance for ClinicalFlow developers.',
};

export default function DevelopersLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <DocsShell>{children}</DocsShell>;
}

