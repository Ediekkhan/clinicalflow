'use client';

import Link from 'next/link';
import { AlertTriangle, ArrowRight, BrainCircuit, CalendarDays, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { ChatBubble } from '@/components/ChatBubble';
import { NetworkToast } from '@/components/NetworkToast';
import { PatientShell } from '@/components/PatientShell';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { demoPatient, demoTriageResult } from '@/lib/syn-data';

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

type Message = {
  id: string;
  role: 'bot' | 'patient';
  kind?: 'text' | 'urgency' | 'appointment' | 'alert';
  body: string;
};

const initialMessage: Message = {
  id: 'hello',
  role: 'bot',
  body: `Hello ${demoPatient.full_name.split(' ')[0]}. I'm your SynaptiVerse health assistant. Please describe what you're experiencing in your own words — you can write in English or Pidgin.`,
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [text, setText] = useState('');
  const [typing, setTyping] = useState(false);
  const [done, setDone] = useState(false);
  const audioRef = useRef<AudioContext | null>(null);

  function playCriticalChime() {
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) return;
    audioRef.current = audioRef.current ?? new AudioContextCtor();
    const oscillator = audioRef.current.createOscillator();
    const gain = audioRef.current.createGain();
    oscillator.frequency.value = 660;
    gain.gain.value = 0.04;
    oscillator.connect(gain);
    gain.connect(audioRef.current.destination);
    oscillator.start();
    oscillator.stop(audioRef.current.currentTime + 0.22);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) return;
    const patientMessage: Message = { id: crypto.randomUUID(), role: 'patient', body: text };
    setMessages((current) => [...current, patientMessage]);
    const critical = /chest|breathe|collapse|bleeding|convulsion/i.test(text);
    setText('');
    setTyping(true);

    if (critical) {
      playCriticalChime();
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'bot',
          kind: 'alert',
          body: '⚠️ This appears to be a medical emergency. Please proceed to the nearest emergency room immediately or call 112.',
        },
      ]);
    }

    window.setTimeout(() => {
      setTyping(false);
      const result = critical
        ? { ...demoTriageResult, urgency: 'CRITICAL' as const, condition_name: 'Acute Myocardial Infarction', specialty: 'Cardiologist' }
        : demoTriageResult;
      const sequence: Message[] = [
        { id: crypto.randomUUID(), role: 'bot', body: "I've analyzed your symptoms and matched them against the SynaptiVerse clinical graph." },
        { id: crypto.randomUUID(), role: 'bot', kind: 'urgency', body: result.severity_message },
        { id: crypto.randomUUID(), role: 'bot', body: `Based on your location, I'm routing you to ${result.nearest_clinic.clinic_name}, ${result.nearest_clinic.distance_km}km away.` },
        { id: crypto.randomUUID(), role: 'bot', kind: 'appointment', body: 'Appointment prepared' },
      ];
      sequence.forEach((message, index) => {
        window.setTimeout(() => {
          setMessages((current) => [...current, message]);
          if (index === sequence.length - 1) setDone(true);
        }, index * 800);
      });
    }, 1500);
  }

  useEffect(
    () => () => {
      void audioRef.current?.close();
    },
    [],
  );

  return (
    <PatientShell>
      <NetworkToast mode="connected" />
      <main className="mx-auto flex h-[calc(100vh-145px)] max-w-4xl flex-col p-4 md:p-6">
        <header className="mb-4 flex items-center justify-between rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <BrainCircuit className="h-6 w-6 text-[#2563EB]" />
            <div>
              <h1 className="font-bold text-[#111827]">SynaptiVerse AI Triage</h1>
              <p className="text-sm text-[#2563EB]">● Live</p>
            </div>
          </div>
        </header>
        <section className="flex-1 overflow-y-auto rounded-card border border-[#E5E7EB] bg-[#F7F8FA] p-4">
          <div className="grid gap-4">
            {messages.map((message) => (
              <ChatBubble key={message.id} role={message.role}>
                {message.kind === 'urgency' ? (
                  <div className="grid gap-3">
                    <UrgencyBadge level={/emergency|critical/i.test(message.body) ? 'CRITICAL' : demoTriageResult.urgency} />
                    <p className="font-bold text-[#111827]">{demoTriageResult.condition_name}</p>
                    <p>{message.body}</p>
                  </div>
                ) : message.kind === 'appointment' ? (
                  <div className="grid gap-3">
                    <CalendarDays className="h-5 w-5 text-[#2563EB]" />
                    <p className="font-bold text-[#111827]">Today · 1:00 PM</p>
                    <p>{demoTriageResult.appointment_slot.specialist_name} · {demoTriageResult.appointment_slot.specialty}</p>
                  </div>
                ) : message.kind === 'alert' ? (
                  <div className="flex gap-3 text-[#DC2626]">
                    <AlertTriangle className="h-5 w-5 shrink-0" />
                    <p className="font-bold">{message.body}</p>
                  </div>
                ) : (
                  message.body
                )}
              </ChatBubble>
            ))}
            {typing ? (
              <ChatBubble role="bot">
                <span className="inline-flex gap-1">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-[#2563EB]" />
                  <span className="h-2 w-2 animate-pulse rounded-full bg-[#2563EB] [animation-delay:120ms]" />
                  <span className="h-2 w-2 animate-pulse rounded-full bg-[#2563EB] [animation-delay:240ms]" />
                </span>
              </ChatBubble>
            ) : null}
          </div>
        </section>
        {done ? (
          <Link href="/queue-status" className="touch-target mt-4 inline-flex items-center justify-center gap-2 bg-[#2563EB] text-white hover:bg-blue-700">
            View My Ticket
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : null}
        <form onSubmit={submit} className="mt-4 grid gap-3 rounded-card border border-[#E5E7EB] bg-white p-3 shadow-sm">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="min-h-24 rounded-lg border border-[#E5E7EB] px-4 py-3 text-sm outline-none focus:border-[#2563EB]"
            placeholder="Write what you are experiencing..."
          />
          <button className="front-desk-target inline-flex items-center justify-center gap-2 bg-[#2563EB] text-white hover:bg-blue-700">
            Send
            <Send className="h-5 w-5" />
          </button>
        </form>
      </main>
    </PatientShell>
  );
}
