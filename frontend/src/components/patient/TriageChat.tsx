'use client';

import { useState } from 'react';
import { ArrowRight, Calendar, MapPin, Mic, Phone } from 'lucide-react';
import { Badge } from '@/components/shared/Badge';

const botMessages = [
  'Reading your symptoms...',
  'This matches warning signs that need a cardiologist review today.',
  'Based on your location, I found Ibom Specialist Hospital, 2.3km away.',
  'Your appointment has been booked with Dr. Effiong Bassey today at 3:00 PM.',
];

export function TriageChat() {
  const [text, setText] = useState('');
  const [submitted, setSubmitted] = useState(false);

  return (
    <section className="flex min-h-[calc(100vh-11rem)] flex-col overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-semibold text-slate-900">SynaptiVerse AI</h2>
          <p className="text-xs text-slate-400">Powered by Claude</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">
          <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
          Live
        </span>
      </header>
      <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-5">
        <div className="max-w-[82%] rounded-2xl rounded-bl-sm bg-white p-4 text-sm text-slate-700 shadow-sm">
          Hello Adaeze. Tell me what you are experiencing. Use English, Pidgin, or whatever feels natural.
        </div>
        {submitted ? (
          <>
            <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-[#2563EB] p-4 text-sm text-white">{text}</div>
            <div className="max-w-[85%] rounded-2xl bg-white p-4 shadow-sm">
              <Badge tone="urgent">URGENT</Badge>
              <h3 className="mt-3 font-semibold text-slate-900">Possible cardiac warning signs</h3>
              <p className="mt-2 text-sm text-slate-600">Chest pain with shortness of breath needs same-day specialist review. If pain worsens, call emergency services immediately.</p>
            </div>
            <div className="max-w-[85%] rounded-2xl border border-blue-100 bg-white p-4 shadow-sm">
              <div className="flex gap-3">
                <MapPin className="h-5 w-5 text-[#2563EB]" />
                <div>
                  <p className="font-semibold text-slate-900">Ibom Specialist Hospital</p>
                  <p className="text-sm text-slate-500">2.3km away - Dr. Effiong Bassey, Cardiologist</p>
                </div>
              </div>
            </div>
            <div className="max-w-[85%] rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="flex gap-3">
                <Calendar className="h-5 w-5 text-[#2563EB]" />
                <div>
                  <p className="font-semibold text-slate-900">Appointment booked</p>
                  <p className="text-sm text-slate-500">Today - 3:00 PM - Room 4</p>
                  <button className="mt-3 rounded-lg bg-[#2563EB] px-3 py-2 text-xs font-semibold text-white">View Ticket</button>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
              <p className="font-bold">MEDICAL EMERGENCY</p>
              <p className="mt-1 text-sm">If you are currently having crushing chest pain or cannot breathe, go to the nearest emergency room now or call 112.</p>
              <a href="tel:112" className="mt-3 inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white">
                <Phone className="h-4 w-4" />
                Call 112
              </a>
            </div>
          </>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-500">
            Previous session - June 18 - tap to expand
          </div>
        )}
      </div>
      <footer className="border-t border-slate-100 bg-white p-4">
        <div className="relative">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            minLength={2}
            maxLength={2000}
            placeholder="Describe how you feel..."
            className="min-h-24 w-full resize-none rounded-2xl border border-slate-200 p-4 pr-24 text-sm outline-none transition focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100"
          />
          <span className="absolute right-4 top-3 text-xs text-slate-400">{text.length}/2000</span>
        </div>
        <div className="mt-3 flex justify-end gap-2">
          <button className="grid h-11 w-11 place-items-center rounded-xl border border-slate-200 text-slate-600">
            <Mic className="h-5 w-5" />
          </button>
          <button
            disabled={!text.trim()}
            onClick={() => setSubmitted(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            Send
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        <div className="sr-only">{botMessages.join(' ')}</div>
      </footer>
    </section>
  );
}

