import { redirect } from 'next/navigation';

export default function MyVisitPage() {
  redirect('/dashboard/queue');
}
