'use client';

import { MessageSquareText } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '@/lib/auth';

type SmsTemplate = { id: string; body: string; max_segments: number };

export default function SmsCanvasPage() {
  const [templates, setTemplates] = useState<SmsTemplate[]>([]);

  useEffect(() => {
    void api.get('/api/v1/channels/templates').then((data) => setTemplates(((data as { sms?: SmsTemplate[] })?.sms ?? []))).catch(console.error);
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto grid max-w-4xl gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">SMS Gateway Pipeline</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Low-bandwidth text templates</h1>
        </div>
        <div className="grid gap-3">
          {templates.map((template) => (
            <article key={template.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-5 w-5 text-blue-600" />
                <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">{template.id.replace('_', ' ')}</h2>
              </div>
              <p className="mt-3 font-mono text-sm leading-6 text-slate-900">{template.body}</p>
              <p className="mt-2 text-sm text-slate-600">{template.body.length} characters before token expansion.</p>
              <p className="mt-1 text-xs font-semibold text-blue-600">Maximum {template.max_segments} SMS segments</p>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}

