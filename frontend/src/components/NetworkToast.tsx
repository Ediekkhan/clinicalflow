'use client';

import { cn } from '@/lib/utils';
import type { NetworkMode } from '@/lib/types';
import type { NetworkState } from '@/types';

type Mode = NetworkMode | NetworkState;

const copy: Record<Mode, string> = {
  connected: '● Connected to live clinic stream',
  reconnecting: '⚡ Syncing...',
  offline: '⚠️ Offline — changes will sync on reconnect',
};

const classes: Record<Mode, string> = {
  connected: 'bg-emerald-600 text-white',
  reconnecting: 'bg-amber-500 text-white animate-pulse',
  offline: 'bg-rose-600 text-white',
};

export function NetworkToast({ mode }: { mode: Mode }) {
  return (
    <div className={cn('fixed inset-x-0 top-0 z-50 flex h-12 items-center justify-center px-4 text-center text-sm font-semibold', classes[mode])}>
      {copy[mode]}
    </div>
  );
}
