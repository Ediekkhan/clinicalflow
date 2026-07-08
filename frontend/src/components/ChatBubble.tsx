import { BrainCircuit } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ChatBubble({
  role,
  children,
}: {
  role: 'bot' | 'patient';
  children: React.ReactNode;
}) {
  const isBot = role === 'bot';
  return (
    <div className={cn('flex gap-3', isBot ? 'justify-start' : 'justify-end')}>
      {isBot ? (
        <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#2563EB] text-white">
          <BrainCircuit className="h-5 w-5" />
        </div>
      ) : null}
      <div
        className={cn(
          'max-w-[82%] rounded-card px-4 py-3 text-sm leading-6 shadow-sm',
          isBot ? 'bg-white text-[#111827]' : 'bg-[#2563EB] text-white',
        )}
      >
        {children}
      </div>
    </div>
  );
}

