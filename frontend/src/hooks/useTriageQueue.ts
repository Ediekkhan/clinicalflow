'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { escalateTicket, listTickets, updateTicket } from '@/lib/api';
import { type NetworkMode, type QueueStatus, type Ticket, type WebSocketEvent } from '@/lib/types';

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? 'ws://localhost:8000';
const pendingKey = 'synaptiverse.pending-queue-actions';

type PendingAction =
  | { type: 'escalate'; ticketId: string }
  | { type: 'status'; ticketId: string; queue_status: QueueStatus };

function upsertTicket(tickets: Ticket[], incoming: Ticket) {
  const next = tickets.filter((ticket) => ticket.id !== incoming.id);
  if (incoming.urgency_level === 'CRITICAL' || incoming.is_manually_escalated) {
    return [{ ...incoming, pulse: incoming.is_manually_escalated }, ...next];
  }
  return [...next, incoming].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
}

function loadPending(): PendingAction[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(window.localStorage.getItem(pendingKey) ?? '[]') as PendingAction[];
  } catch {
    return [];
  }
}

function savePending(actions: PendingAction[]) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(pendingKey, JSON.stringify(actions));
  }
}

export function useTriageQueue() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [networkMode, setNetworkMode] = useState<NetworkMode>('reconnecting');
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  const applyPending = useCallback((action: PendingAction) => {
    setTickets((current) => {
      if (action.type === 'escalate') {
        const target = current.find((ticket) => ticket.id === action.ticketId);
        if (!target) return current;
        const moved: Ticket = {
          ...target,
          urgency_level: 'CRITICAL',
          is_manually_escalated: true,
          pendingSync: true,
          pulse: true,
        };
        return [moved, ...current.filter((ticket) => ticket.id !== action.ticketId)];
      }
      return current.map((ticket) =>
        ticket.id === action.ticketId
          ? { ...ticket, queue_status: action.queue_status, pendingSync: true }
          : ticket,
      );
    });
  }, []);

  const enqueue = useCallback(
    (action: PendingAction) => {
      applyPending(action);
      setPendingActions((current) => {
        const next = [...current, action];
        savePending(next);
        return next;
      });
    },
    [applyPending],
  );

  const flushPending = useCallback(async () => {
    const actions = loadPending();
    if (!actions.length) return;
    setNetworkMode('reconnecting');
    const remaining: PendingAction[] = [];
    for (const action of actions) {
      try {
        if (action.type === 'escalate') {
          const synced = await escalateTicket(action.ticketId);
          setTickets((current) => upsertTicket(current, { ...synced, pendingSync: false, pulse: true }));
        } else {
          const synced = await updateTicket(action.ticketId, { queue_status: action.queue_status });
          setTickets((current) => upsertTicket(current, { ...synced, pendingSync: false }));
        }
      } catch {
        remaining.push(action);
      }
    }
    setPendingActions(remaining);
    savePending(remaining);
    setNetworkMode(remaining.length ? 'offline' : 'connected');
  }, []);

  useEffect(() => {
    setPendingActions(loadPending());
    listTickets()
      .then((loaded) => setTickets(loaded))
      .catch(() => {
        setTickets([]);
        setNetworkMode('offline');
      });
  }, []);

  useEffect(() => {
    let reconnectTimer: number | undefined;
    let heartbeat: number | undefined;
    let closedByCleanup = false;

    function connect() {
      const tenantId = process.env.NEXT_PUBLIC_TENANT_ID;
      const query = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
      const socket = new WebSocket(`${WS_BASE}/api/v1/ws/triage${query}`);
      socketRef.current = socket;

      socket.onopen = () => {
        setNetworkMode('connected');
        void flushPending();
        heartbeat = window.setInterval(() => socket.send('ping'), 25000);
      };

      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as WebSocketEvent;
        if ('ticket_number' in event.payload) {
          setTickets((current) => upsertTicket(current, { ...(event.payload as Ticket), pendingSync: false }));
        }
      };

      socket.onerror = () => {
        setNetworkMode('reconnecting');
      };

      socket.onclose = () => {
        if (heartbeat) window.clearInterval(heartbeat);
        if (closedByCleanup) return;
        setNetworkMode((current) => (current === 'offline' ? 'offline' : 'reconnecting'));
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
    const online = () => {
      setNetworkMode('reconnecting');
      void flushPending();
    };
    window.addEventListener('offline', offline);
    window.addEventListener('online', online);
    return () => {
      window.removeEventListener('offline', offline);
      window.removeEventListener('online', online);
    };
  }, [flushPending]);

  const forceOvertake = useCallback(
    async (ticketId: string) => {
      if (networkMode === 'connected') {
        applyPending({ type: 'escalate', ticketId });
        try {
          const synced = await escalateTicket(ticketId);
          setTickets((current) => upsertTicket(current, { ...synced, pendingSync: false, pulse: true }));
        } catch {
          enqueue({ type: 'escalate', ticketId });
          setNetworkMode('offline');
        }
      } else {
        enqueue({ type: 'escalate', ticketId });
      }
    },
    [applyPending, enqueue, networkMode],
  );

  const setStatus = useCallback(
    async (ticketId: string, queue_status: QueueStatus) => {
      if (networkMode === 'connected') {
        applyPending({ type: 'status', ticketId, queue_status });
        try {
          const synced = await updateTicket(ticketId, { queue_status });
          setTickets((current) => upsertTicket(current, { ...synced, pendingSync: false }));
        } catch {
          enqueue({ type: 'status', ticketId, queue_status });
          setNetworkMode('offline');
        }
      } else {
        enqueue({ type: 'status', ticketId, queue_status });
      }
    },
    [applyPending, enqueue, networkMode],
  );

  const grouped = useMemo(
    () => ({
      CRITICAL: tickets.filter((ticket) => ticket.urgency_level === 'CRITICAL' && ticket.queue_status !== 'RESOLVED'),
      URGENT: tickets.filter((ticket) => ticket.urgency_level === 'URGENT' && ticket.queue_status !== 'RESOLVED'),
      ROUTINE: tickets.filter((ticket) => ticket.urgency_level === 'ROUTINE' && ticket.queue_status !== 'RESOLVED'),
    }),
    [tickets],
  );

  return {
    tickets,
    grouped,
    networkMode,
    pendingActions,
    forceOvertake,
    setStatus,
  };
}
