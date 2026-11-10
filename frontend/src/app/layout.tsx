import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ClinicalFlow',
  description: 'Your AI Health Companion.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-ui antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
