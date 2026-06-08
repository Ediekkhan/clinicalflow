import { AlertTriangle, MessageCircle, Radio } from 'lucide-react';

const rows = [
  ['continue_existing', 'Continue existing visit', 'Use the active ticket on this phone.'],
  ['register_new_patient', 'Register a new patient', 'Create a separate ticket under this shared phone group.'],
  ['book_slot', 'Book appointment slot', 'Show the next available provider times.'],
];

export default function WhatsAppCanvasPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto grid max-w-4xl gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Meta Cloud API Canvas</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">WhatsApp conversational triage</h1>
        </div>
        <section className="rounded-lg border border-slate-200 bg-white p-4 md:p-6">
          <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
            <MessageCircle className="h-6 w-6 text-emerald-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Existing visit found</h2>
              <p className="text-sm text-slate-600">This phone already has an active clinic visit: SV-2026-9402.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3">
            {rows.map(([id, title, description]) => (
              <label key={id} className="data-row flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50">
                <Radio className="h-5 w-5 text-emerald-600" />
                <span>
                  <span className="block text-sm font-bold text-slate-900">{title}</span>
                  <span className="block text-sm text-slate-600">{description}</span>
                </span>
              </label>
            ))}
          </div>
        </section>
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-4">
          <div className="flex gap-3">
            <AlertTriangle className="h-6 w-6 shrink-0 text-rose-600" />
            <p className="text-sm font-semibold leading-6 text-rose-700">
              RED ALERT: If dangerous medical keywords are parsed, the webhook returns an immediate emergency message before normal appointment menus.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

