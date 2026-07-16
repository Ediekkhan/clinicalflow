'use client';

import { AlertTriangle, MessageCircle, Radio } from 'lucide-react';
import { useState } from 'react';
import { api } from '@/lib/auth';

const rows = [
  ['continue_existing', 'Continue existing visit', 'Use the active ticket on this phone.'],
  ['register_new_patient', 'Register a new patient', 'Create a separate ticket under this shared phone group.'],
  ['book_slot', 'Book appointment slot', 'Show the next available provider times.'],
];

export default function WhatsAppCanvasPage() {
  const [phone, setPhone] = useState('+2348012345678');
  const [message, setMessage] = useState('I have fever and weakness');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  async function send(intent?: string) {
    setLoading(true);
    try {
      const payload = await api.post('/api/v1/channels/whatsapp/intake', {
        customer_phone: phone,
        raw_intake_text: message,
        ...(intent ? { intent } : {}),
      });
      setResult((payload ?? null) as Record<string, unknown> | null);
    } finally {
      setLoading(false);
    }
  }

  const menu = Array.isArray(result?.menu) ? result.menu as Array<{ id: string; title: string; description: string }> : [];

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto grid max-w-4xl gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Meta Cloud API Canvas</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">WhatsApp conversational triage</h1>
        </div>
        <section className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 md:p-6">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Live channel simulator</h2>
            <p className="mt-1 text-sm text-slate-600">Send the same phone twice to demonstrate duplicate-family interception.</p>
          </div>
          <input value={phone} onChange={(event) => setPhone(event.target.value)} aria-label="Customer phone" className="rounded-lg border border-slate-300 px-4 py-2.5" />
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} aria-label="Intake message" className="min-h-24 rounded-lg border border-slate-300 px-4 py-2.5" />
          <button type="button" disabled={loading} onClick={() => void send()} className="front-desk-target bg-blue-600 text-white disabled:bg-slate-300">
            {loading ? 'Sending…' : 'Send WhatsApp intake'}
          </button>
          {result ? (
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-blue-600">{String(result.action ?? 'Response')}</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">{String(result.message ?? '')}</p>
              {menu.length ? (
                <div className="mt-4 grid gap-2">
                  {menu.map((option) => (
                    <button key={option.id} type="button" onClick={() => void send(option.id)} className="data-row rounded-lg border border-slate-200 bg-white text-left">
                      <span className="block text-sm font-bold text-slate-900">{option.title}</span>
                      <span className="block text-sm text-slate-600">{option.description}</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-4 md:p-6">
          <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
            <MessageCircle className="h-6 w-6 text-blue-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Existing visit found</h2>
              <p className="text-sm text-slate-600">This phone already has an active clinic visit.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3">
            {rows.map(([id, title, description]) => (
              <label key={id} className="data-row flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50">
                <Radio className="h-5 w-5 text-blue-600" />
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

