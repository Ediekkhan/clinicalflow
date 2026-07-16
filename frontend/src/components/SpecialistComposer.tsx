'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { EntityDashboard } from '@/components/entity/EntityDashboard';
import { api } from '@/lib/auth';

type Ticket = { id: string; ticket_number?: string; assigned_to_me?: boolean };

export function SpecialistComposer({ mode }: { mode: 'notes' | 'messages' }) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticketId, setTicketId] = useState('');
  const [body, setBody] = useState('');
  const [senderLabel, setSenderLabel] = useState('Specialist');
  const [feedback, setFeedback] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode !== 'notes') return;
    api.get('/api/v1/specialist/patients?assigned_only=true').then((payload) => {
      const items = (payload?.items ?? []) as Ticket[];
      setTickets(items);
      setTicketId(items[0]?.id ?? '');
    }).catch(() => setFeedback('Unable to load assigned patients.'));
  }, [mode]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true); setFeedback('');
    try {
      if (mode === 'notes') await api.post(`/api/v1/specialist/patients/${ticketId}/notes`, { body });
      else await api.post('/api/v1/specialist/messages', { body, sender_label: senderLabel });
      setBody('');
      setFeedback(mode === 'notes' ? 'Consultation note saved.' : 'Message sent.');
      window.dispatchEvent(new Event('clinicalflow:refresh'));
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Unable to save.');
    } finally { setSaving(false); }
  }

  const notes = mode === 'notes';
  const composer = (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">{notes ? 'Add consultation note' : 'Compose secure message'}</h2>
        <form onSubmit={submit} className="mt-4 grid gap-3">
          {notes ? <select required value={ticketId} onChange={(event) => setTicketId(event.target.value)} className="rounded-xl border border-slate-200 px-4 py-3"><option value="">Select assigned patient</option>{tickets.map((ticket) => <option key={ticket.id} value={ticket.id}>{ticket.ticket_number ?? ticket.id}</option>)}</select> : <input required value={senderLabel} onChange={(event) => setSenderLabel(event.target.value)} placeholder="Sender label" className="rounded-xl border border-slate-200 px-4 py-3" />}
          <textarea required minLength={notes ? 3 : 2} value={body} onChange={(event) => setBody(event.target.value)} placeholder={notes ? 'Clinical observations, assessment, and plan' : 'Write a secure message'} rows={4} className="rounded-xl border border-slate-200 px-4 py-3" />
          <button disabled={saving || (notes && !ticketId)} className="w-fit rounded-xl bg-blue-600 px-5 py-3 font-bold text-white disabled:opacity-60">{saving ? 'Saving…' : notes ? 'Save note' : 'Send message'}</button>
        </form>
        {feedback ? <p className="mt-3 text-sm text-slate-600" role="status">{feedback}</p> : null}
      </section>
  );
  return <EntityDashboard entity="specialist" view={mode} title={notes ? 'Consultation Notes' : 'Messages'} subtitle={notes ? 'Search and manage clinical notes across all patient encounters.' : 'Secure communication with patients, nurses, and partner facilities.'}>{composer}</EntityDashboard>;
}
