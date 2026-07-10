'use client';

import { useEffect, useState } from 'react';
import { Volume2 } from 'lucide-react';
import { api } from '@/lib/auth';

type WaitingRoomPayload = {
  now_serving?: { ticket_number?: string; room_label?: string; patient_name?: string } | null;
  up_next?: { id?: string; ticket_number?: string; room_label?: string }[];
  departments?: { name?: string; waiting?: number; being_seen?: number; resolved?: number }[];
};

export default function HospitalWaitingRoomPage() {
  const [payload, setPayload] = useState<WaitingRoomPayload | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const nowServing = payload?.now_serving ?? null;
  const announcement = nowServing?.ticket_number ? `Now serving ${nowServing.ticket_number}${nowServing.room_label ? ` in ${nowServing.room_label}` : ''}` : '';

  useEffect(() => {
    let cancelled = false;
    async function loadWaitingRoom() {
      try {
        const data = await api.get('/api/v1/hospital/waiting-room');
        if (!cancelled) setPayload((data ?? {}) as WaitingRoomPayload);
      } catch (error) {
        console.error(error);
        if (!cancelled) setPayload({});
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadWaitingRoom();
    const interval = window.setInterval(loadWaitingRoom, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!announcement || !('speechSynthesis' in window)) return;
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
          {isLoading ? (
            <div className="mx-auto mt-6 h-24 max-w-xl animate-pulse rounded bg-white/10" />
          ) : nowServing?.ticket_number ? (
            <>
              <p className="mt-6 break-words font-mono text-4xl font-bold tracking-tight text-white sm:text-6xl md:text-8xl">{nowServing.ticket_number}</p>
              {nowServing.room_label ? <p className="mt-6 text-3xl font-bold tracking-tight text-blue-300 sm:text-4xl md:text-6xl">IN {nowServing.room_label.toUpperCase()}</p> : null}
            </>
          ) : (
            <p className="mt-6 text-2xl font-semibold text-slate-300">No active queue</p>
          )}
        </div>
        {payload?.up_next?.length ? (
          <div className="rounded-card border border-white/10 bg-white/5 p-5">
            <p className="text-sm font-bold uppercase tracking-wider text-slate-400">Up Next</p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {payload.up_next.slice(0, 2).map((item) => (
                <div key={item.id ?? item.ticket_number} className="rounded-xl bg-white/10 p-4 font-mono text-xl font-bold">{item.ticket_number}</div>
              ))}
            </div>
          </div>
        ) : null}
        {announcement ? (
          <div className="mx-auto inline-flex items-center justify-center gap-3 rounded-lg bg-white/5 px-5 py-4 text-lg font-semibold text-slate-200">
            <Volume2 className="h-6 w-6 text-blue-300" />
            {announcement}
          </div>
        ) : null}
      </section>
    </main>
  );
}
