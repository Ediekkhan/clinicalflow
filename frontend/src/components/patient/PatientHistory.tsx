import { Badge } from '@/components/shared/Badge';

const events = [
  ['CRITICAL triage', 'Possible cardiac event', 'Dr. Effiong Bassey', 'Follow-up needed', 'rose'],
  ['Appointment', 'Cardiology review', 'Ibom Specialist Hospital', 'Completed', 'sky'],
  ['Prescription', 'Amlodipine 5mg', 'Dr. Okon', 'Downloaded', 'violet'],
  ['ROUTINE triage', 'Malaria screening', 'Uyo Family Clinic', 'Resolved', 'sky'],
];

export function PatientHistory() {
  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <div className="mb-5 flex flex-wrap gap-2">
        {['All', 'Triage Sessions', 'Appointments', 'Prescriptions'].map((filter, index) => (
          <button key={filter} className={`rounded-full px-4 py-2 text-sm font-semibold ${index === 0 ? 'bg-[#2563EB] text-white' : 'bg-slate-100 text-slate-600'}`}>{filter}</button>
        ))}
      </div>
      <div className="relative space-y-5 border-l border-slate-200 pl-6">
        {events.map((event) => (
          <article key={event[1]} className="relative rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
            <span className={`absolute -left-[31px] top-5 h-3 w-3 rounded-full ${event[4] === 'rose' ? 'bg-rose-500' : event[4] === 'sky' ? 'bg-blue-500' : event[4] === 'violet' ? 'bg-violet-500' : 'bg-blue-500'}`} />
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">June 19, 2026 - 10:20 AM</p>
                <h3 className="mt-1 font-semibold text-slate-900">{event[1]}</h3>
                <p className="mt-1 text-sm text-slate-500">{event[2]}</p>
              </div>
              <Badge tone={event[4] === 'rose' ? 'rose' : event[4] === 'sky' ? 'success' : event[4] === 'violet' ? 'violet' : 'routine'}>{event[3]}</Badge>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

