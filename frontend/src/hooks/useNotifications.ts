'use client';

import { useMemo, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { demoNotifications, demoSpecialist } from '@/lib/syn-data';
import type { SynNotification } from '@/types';

export function useNotifications() {
  const [notifications, setNotifications] = useState<SynNotification[]>(demoNotifications);
  const networkState = useWebSocket<{ payload?: SynNotification }>(`/api/v1/ws/specialist/${demoSpecialist.id}`, (event) => {
    const notification = event.payload;
    if (!notification) return;
    setNotifications((current) => [{ ...notification, is_read: false }, ...current]);
  });

  const unreadCount = useMemo(() => notifications.filter((item) => !item.is_read).length, [notifications]);

  function markAllRead() {
    setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
  }

  function markRead(id: string) {
    setNotifications((current) => current.map((item) => (item.id === id ? { ...item, is_read: true } : item)));
  }

  return { notifications, unreadCount, networkState, markAllRead, markRead };
}
