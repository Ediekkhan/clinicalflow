'use client';

import { useEffect, useMemo, useState } from 'react';
import { Volume2 } from 'lucide-react';
import { demoTickets } from '@/lib/demo-data';

export default function HospitalWaitingRoomPage() {
  const [index, setIndex] = useState(0);
  const ticket = demoTickets[index % demoTickets.length];
  const room = useMemo(() => (ticket.urgency_level === 'CRITICAL' ? 'Room 4' : 'Room 2'), [ticket.urgency_level]);
  const announcement = `Now serving ${ticket.ticket_number} in ${room}`;

  useEffect(() => {
    const interval = window.setInterval(() => setIndex((current) => current + 1), 9000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const utterance = new SpeechSynthesisUtterance(announcement);
    utterance.rate = 0.85;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }, [announcement]);

  return (
    <main className="grid min-h-screen place-items-center bg-[#0D1117] p-4 text-white md:p-6">
      <section className="grid w-full max-w-6xl gap-8 text-center">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-blue-300">Hospital Waiting Room</p>
          <h1 className="font-display text-4xl">SynaptiVerse</h1>
        </div>
        <div className="rounded-card border border-white/10 bg-white/5 p-6 md:p-10">
          <p className="text-sm font-bold uppercase tracking-wider text-slate-400">Now Serving</p>
          <p className="mt-6 break-words font-mono text-4xl font-bold tracking-tight text-white sm:text-6xl md:text-8xl">#{ticket.ticket_number}</p>
          <p className="mt-6 text-3xl font-bold tracking-tight text-blue-300 sm:text-4xl md:text-6xl">IN {room.toUpperCase()}</p>
        </div>
        <div className="mx-auto inline-flex items-center justify-center gap-3 rounded-lg bg-white/5 px-5 py-4 text-lg font-semibold text-slate-200">
          <Volume2 className="h-6 w-6 text-blue-300" />
          {announcement}
        </div>
      </section>
    </main>
  );
}
