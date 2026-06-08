'use client';

import { useMemo, useState } from 'react';
import { Calculator, Send } from 'lucide-react';

export function RoiCalculator() {
  const [dailyCapacity, setDailyCapacity] = useState(120);
  const [minutesSaved, setMinutesSaved] = useState(7);

  const roi = useMemo(() => {
    const dailyHours = (dailyCapacity * minutesSaved) / 60;
    const monthlyHours = dailyHours * 22;
    const extraVisits = Math.round(monthlyHours * 4);
    return { dailyHours, monthlyHours, extraVisits };
  }, [dailyCapacity, minutesSaved]);

  return (
    <section className="grid gap-6 rounded-lg border border-slate-200 bg-white p-4 md:p-6">
      <div className="flex items-center gap-3">
        <span className="rounded-lg bg-emerald-50 p-3 text-emerald-600">
          <Calculator className="h-6 w-6" />
        </span>
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">CMD ROI Calculator</p>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Clinic time unlocked</h2>
        </div>
      </div>
      <div className="grid gap-5">
        <label className="grid gap-3 text-sm font-medium text-slate-700">
          Daily outpatient capacity: {dailyCapacity}
          <input
            type="range"
            min={20}
            max={600}
            value={dailyCapacity}
            onChange={(event) => setDailyCapacity(Number(event.target.value))}
            className="accent-emerald-600"
          />
        </label>
        <label className="grid gap-3 text-sm font-medium text-slate-700">
          Minutes saved per patient: {minutesSaved}
          <input
            type="range"
            min={2}
            max={20}
            value={minutesSaved}
            onChange={(event) => setMinutesSaved(Number(event.target.value))}
            className="accent-emerald-600"
          />
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Daily hours</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{roi.dailyHours.toFixed(1)}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Monthly hours</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{roi.monthlyHours.toFixed(0)}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-sm font-medium uppercase tracking-wider text-slate-500">Recovered visits</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{roi.extraVisits}</p>
        </div>
      </div>
      <form className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input
          className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
          placeholder="operations@clinic.ng"
          type="email"
        />
        <button className="touch-target inline-flex items-center justify-center gap-2 bg-emerald-600 text-white hover:bg-emerald-700">
          <Send className="h-4 w-4" />
          Request demo
        </button>
      </form>
    </section>
  );
}

