'use client';

import { useEffect, useRef, useState } from 'react';
import type { NetworkState } from '@/types';

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE_URL ?? process.env.NEXT_PUBLIC_WS_BASE ?? 'ws://127.0.0.1:8000';
const delays = [1000, 2000, 4000, 8000, 16000];

export function useWebSocket<TMessage>(path: string, onMessage?: (message: TMessage) => void) {
  const [networkState, setNetworkState] = useState<NetworkState>('reconnecting');
  const retryRef = useRef(0);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let heartbeat: number | undefined;
    let closed = false;

    function connect() {
      socket = new WebSocket(`${WS_BASE}${path}`);

      socket.onopen = () => {
        retryRef.current = 0;
        setNetworkState('connected');
        heartbeat = window.setInterval(() => socket?.send('ping'), 25000);
      };

      socket.onmessage = (event) => {
        try {
          onMessageRef.current?.(JSON.parse(event.data) as TMessage);
        } catch {
          onMessageRef.current?.(event.data as TMessage);
        }
      };

      socket.onerror = () => setNetworkState('reconnecting');

      socket.onclose = () => {
        if (heartbeat) window.clearInterval(heartbeat);
        if (closed) return;
        const attempt = retryRef.current;
        if (attempt >= delays.length) {
          setNetworkState('offline');
          return;
        }
        setNetworkState('reconnecting');
        retryTimer = window.setTimeout(() => {
          retryRef.current = attempt + 1;
          connect();
        }, delays[attempt]);
      };
    }

    connect();
    return () => {
      closed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      if (heartbeat) window.clearInterval(heartbeat);
      socket?.close();
    };
  }, [path]);

  return networkState;
}

