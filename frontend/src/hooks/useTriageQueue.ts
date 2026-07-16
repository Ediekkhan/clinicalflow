'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, escalateTicket, listTickets, updateTicket } from '@/lib/api';
import { type NetworkMode, type QueueStatus, type Ticket, type WebSocketEvent } from '@/lib/types';

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? process.env.NEXT_PUBLIC_WS_BASE_URL ?? 'ws://localhost:8000';
const pendingKey = 'synaptiverse.pending-queue-actions';

type PendingAction =
  | { id: string; type: 'escalate'; ticketId: string; expectedVersion: number }
  | { id: string; type: 'status'; ticketId: string; queue_status: QueueStatus; expectedVersion: number };

function mutationId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertTicket(tickets: Ticket[], incoming: Ticket) {
  const next = tickets.filter((ticket) => ticket.id !== incoming.id);
  if (incoming.urgency_level === 'CRITICAL' || incoming.is_manually_escalated) return [{ ...incoming, pulse: incoming.is_manually_escalated }, ...next];
  return [...next, incoming].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
}

function applyAction(tickets: Ticket[], action: PendingAction) {
  if (action.type === 'escalate') {
    const target = tickets.find((ticket) => ticket.id === action.ticketId);
    if (!target) return tickets;
    const moved: Ticket = { ...target, urgency_level: 'CRITICAL', is_manually_escalated: true, pendingSync: true, pulse: true };
    return [moved, ...tickets.filter((ticket) => ticket.id !== action.ticketId)];
  }
  return tickets.map((ticket) => ticket.id === action.ticketId ? { ...ticket, queue_status: action.queue_status, pendingSync: true } : ticket);
}

function loadPending(): PendingAction[] {
  if (typeof window === 'undefined') return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(pendingKey) ?? '[]') as PendingAction[];
    return parsed.filter((action) => action.id && action.ticketId && action.expectedVersion);
  } catch {
    return [];
  }
}

function savePending(actions: PendingAction[]) {
  if (typeof window !== 'undefined') window.localStorage.setItem(pendingKey, JSON.stringify(actions));
}

export function useTriageQueue() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [networkMode, setNetworkMode] = useState<NetworkMode>('reconnecting');
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  const queueAction = useCallback((action: PendingAction, optimistic = true) => {
    if (optimistic) setTickets((current) => applyAction(current, action));
    setPendingActions((current) => {
      const next = [...current.filter((item) => !(item.ticketId === action.ticketId && item.type === action.type)), action];
      savePending(next);
      return next;
    });
  }, []);

  const flushPending = useCallback(async () => {
    const actions = loadPending();
    const remaining: PendingAction[] = [];
    setNetworkMode('reconnecting');
    for (const action of actions) {
      try {
        if (action.type === 'escalate') await escalateTicket(action.ticketId, action.id, action.expectedVersion);
        else await updateTicket(action.ticketId, { queue_status: action.queue_status, expected_version: action.expectedVersion }, action.id);
      } catch (error) {
        // A 409 means the server has a newer version. Drop the stale action and reconcile below.
        if (!(error instanceof ApiError && error.status === 409)) remaining.push(action);
      }
    }
    try {
      const authoritative = await listTickets();
      setTickets(remaining.reduce((current, action) => applyAction(current, action), authoritative));
      setNetworkMode(remaining.length ? 'offline' : 'connected');
    } catch {
      setNetworkMode('offline');
    }
    setPendingActions(remaining);
    savePending(remaining);
  }, []);

  useEffect(() => {
    const saved = loadPending();
    setPendingActions(saved);
    listTickets()
      .then((loaded) => setTickets(saved.reduce((current, action) => applyAction(current, action), loaded)))
      .catch(() => setNetworkMode('offline'));
  }, []);

  useEffect(() => {
    let reconnectTimer: number | undefined;
    let heartbeat: number | undefined;
    let closedByCleanup = false;
    function connect() {
      const socket = new WebSocket(`${WS_BASE}/api/v1/ws/triage`);
      socketRef.current = socket;
      socket.onopen = () => {
        setNetworkMode('connected');
        void flushPending();
        heartbeat = window.setInterval(() => socket.send('ping'), 25000);
      };
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as WebSocketEvent;
        if ('ticket_number' in event.payload) setTickets((current) => upsertTicket(current, { ...(event.payload as Ticket), pendingSync: false }));
      };
      socket.onerror = () => setNetworkMode('reconnecting');
      socket.onclose = () => {
        if (heartbeat) window.clearInterval(heartbeat);
        if (closedByCleanup) return;
        setNetworkMode((current) => current === 'offline' ? 'offline' : 'reconnecting');
        reconnectTimer = window.setTimeout(connect, 1800);
      };
    }
    connect();
    return () => {
      closedByCleanup = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (heartbeat) window.clearInterval(heartbeat);
      socketRef.current?.close();
    };
  }, [flushPending]);

  useEffect(() => {
    const offline = () => setNetworkMode('offline');
    const online = () => void flushPending();
    window.addEventListener('offline', offline);
    window.addEventListener('online', online);
    return () => {
      window.removeEventListener('offline', offline);
      window.removeEventListener('online', online);
    };
  }, [flushPending]);

  const forceOvertake = useCallback(async (ticketId: string) => {
    const ticket = tickets.find((item) => item.id === ticketId);
    if (!ticket) return;
    const action: PendingAction = { id: mutationId(), type: 'escalate', ticketId, expectedVersion: ticket.version };
    if (networkMode !== 'connected') return queueAction(action);
    setTickets((current) => applyAction(current, action));
    try {
      const synced = await escalateTicket(ticketId, action.id, action.expectedVersion);
      setTickets((current) => upsertTicket(current, { ...synced, pendingSync: false, pulse: true }));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) void flushPending();
      else {
        queueAction(action, false);
        setNetworkMode('offline');
      }
    }
  }, [flushPending, networkMode, queueAction, tickets]);

  const setStatus = useCallback(async (ticketId: string, queue_status: QueueStatus) => {
    const ticket = tickets.find((item) => item.id === ticketId);
    if (!ticket) return;
    const action: PendingAction = { id: mutationId(), type: 'status', ticketId, queue_status, expectedVersion: ticket.version };
    if (networkMode !== 'connected') return queueAction(action);
    setTickets((current) => applyAction(current, action));
    try {
      const synced = await updateTicket(ticketId, { queue_status, expected_version: action.expectedVersion }, action.id);
      setTickets((current) => upsertTicket(current, { ...synced, pendingSync: false }));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) void flushPending();
      else {
        queueAction(action, false);
        setNetworkMode('offline');
      }
    }
  }, [flushPending, networkMode, queueAction, tickets]);

  const grouped = useMemo(() => ({
    CRITICAL: tickets.filter((ticket) => ticket.urgency_level === 'CRITICAL' && ticket.queue_status !== 'RESOLVED'),
    URGENT: tickets.filter((ticket) => ticket.urgency_level === 'URGENT' && ticket.queue_status !== 'RESOLVED'),
    ROUTINE: tickets.filter((ticket) => ticket.urgency_level === 'ROUTINE' && ticket.queue_status !== 'RESOLVED'),
  }), [tickets]);

  return { tickets, grouped, networkMode, pendingActions, forceOvertake, setStatus };
}
