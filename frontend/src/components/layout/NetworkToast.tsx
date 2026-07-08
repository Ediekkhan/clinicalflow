type NetworkToastProps = {
  mode?: 'connected' | 'reconnecting' | 'offline';
};

const copy = {
  connected: { className: 'bg-blue-600', text: 'Connected to live stream' },
  reconnecting: { className: 'animate-pulse bg-amber-500', text: 'Reconnecting...' },
  offline: { className: 'bg-rose-600', text: 'Offline - changes will sync on reconnect' },
};

export function NetworkToast({ mode = 'connected' }: NetworkToastProps) {
  const state = copy[mode];
  return (
    <div className={`fixed left-0 top-0 z-50 hidden h-9 w-full items-center justify-center text-xs font-semibold text-white md:flex ${state.className}`}>
      <span className="mr-2 h-2 w-2 rounded-full bg-white" />
      {state.text}
    </div>
  );
}

