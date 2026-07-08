import { MessageSquareText } from 'lucide-react';

const templates = [
  {
    title: 'Queue assignment',
    body: '[PROJECT_NAME]: Ticket {{ticket_number}}. Urgency: {{urgency}}. Please wait near {{room_hint}}. Reply CANCEL to cancel an appointment.',
  },
  {
    title: 'Booking confirmation',
    body: '[PROJECT_NAME]: {{ticket_number}} booked for {{date}} {{time}}. Reply CANCEL to cancel.',
  },
  {
    title: 'Shift alert',
    body: '[PROJECT_NAME]: Your appointment {{ticket_number}} shifted to {{date}} {{time}}. Please arrive 10 mins early.',
  },
  {
    title: 'Cancellation',
    body: '[PROJECT_NAME]: Appointment for {{ticket_number}} cancelled. Reply BOOK to reschedule.',
  },
];

export default function SmsCanvasPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto grid max-w-4xl gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">SMS Gateway Pipeline</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Low-bandwidth text templates</h1>
        </div>
        <div className="grid gap-3">
          {templates.map((template) => (
            <article key={template.title} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-5 w-5 text-blue-600" />
                <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">{template.title}</h2>
              </div>
              <p className="mt-3 font-mono text-sm leading-6 text-slate-900">{template.body}</p>
              <p className="mt-2 text-sm text-slate-600">{template.body.length} characters before token expansion.</p>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}

