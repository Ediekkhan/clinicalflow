'use client';

import { useEffect, useState } from 'react';
import { NetworkToast } from '@/components/NetworkToast';
import { PatientShell } from '@/components/PatientShell';
import { TicketDisplay } from '@/components/TicketDisplay';
import { useWebSocket } from '@/hooks/useWebSocket';
import { demoPatient, patientTickets } from '@/lib/syn-data';
import type { PatientTicket } from '@/types';

export default function QueueStatusPage() {
  const [ticket, setTicket] = useState<PatientTicket>(patientTickets[0]);
  const [position, setPosition] = useState(3);
  const networkState = useWebSocket<{ payload?: PatientTicket }>(`/api/v1/ws/queue/${demoPatient.card_number}`, (event) => {
    if (event.payload) setTicket(event.payload);
  });

  useEffect(() => {
    const interval = window.setInterval(() => setPosition((current) => Math.max(1, current - 1)), 9000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <PatientShell>
      <NetworkToast mode={networkState} />
      <main className="mx-auto grid max-w-4xl gap-6 p-4 md:p-6">
        <div className="text-center">
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Live Queue Tracker</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">Your visit status</h1>
        </div>
        <TicketDisplay ticket={{ ...ticket, queue_status: position === 1 ? 'BEING_SEEN' : ticket.queue_status }} position={position} />
      </main>
    </PatientShell>
  );
}
