import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { BookingWorkspace } from '@/components/BookingWorkspace';

export default function BookPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-4xl p-4 md:p-6">
        <Link href="/" className="inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-white">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
      </div>
      <BookingWorkspace />
    </main>
  );
}

