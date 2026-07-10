'use client';

import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { api } from '@/lib/auth';
import type { SynNotification } from '@/types';

export function useNotifications() {
  const [notifications, setNotifications] = useState<SynNotification[]>([]);
  const networkState = useWebSocket<{ payload?: SynNotification }>('/api/v1/ws/notifications', (event) => {
    const notification = event.payload;
    if (!notification) return;
    setNotifications((current) => [{ ...notification, is_read: false }, ...current]);
  });

  useEffect(() => {
    let cancelled = false;

    async function loadNotifications() {
      try {
        const data = await api.get('/api/v1/notifications');
        if (!cancelled) setNotifications(Array.isArray(data) ? (data as SynNotification[]) : []);
      } catch (error) {
        console.error(error);
        if (!cancelled) setNotifications([]);
      }
    }

    void loadNotifications();
    return () => {
      cancelled = true;
    };
  }, []);

  const unreadCount = useMemo(() => notifications.filter((item) => !item.is_read).length, [notifications]);

  async function markAllRead() {
    setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
    try {
      await api.patch('/api/v1/notifications/read-all', {});
    } catch (error) {
      console.error(error);
    }
  }

  async function markRead(id: string) {
    setNotifications((current) => current.map((item) => (item.id === id ? { ...item, is_read: true } : item)));
    try {
      await api.patch(`/api/v1/notifications/${id}/read`, {});
    } catch (error) {
      console.error(error);
    }
  }

  return { notifications, unreadCount, networkState, markAllRead, markRead };
}
