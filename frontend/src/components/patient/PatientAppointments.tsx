import { CalendarCheck, Clock, MapPin } from 'lucide-react';
import { Badge } from '@/components/shared/Badge';

const appointments = [
  ['Today 3:00 PM', 'Dr. Effiong Bassey', 'Cardiology', 'Ibom Specialist Hospital', 'CONFIRMED'],
  ['June 23 10:30 AM', 'Dr. Udo Okon', 'General Practice', 'Uyo Family Clinic', 'FOLLOW-UP'],
  ['June 30 9:00 AM', 'Prime Diagnostics', 'Full Blood Count', 'Prime Diagnostics Lab', 'LAB'],
];

export function PatientAppointments() {
  return (
    <section className="grid gap-4">
      {appointments.map((appointment) => (
        <article key={appointment[0]} className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex gap-4">
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-[#2563EB]">
                <CalendarCheck className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900">{appointment[1]}</h3>
                <p className="text-sm text-slate-500">{appointment[2]}</p>
                <p className="mt-2 flex items-center gap-2 text-sm text-slate-500">
                  <MapPin className="h-4 w-4" />
                  {appointment[3]}
                </p>
              </div>
            </div>
            <div className="text-right">
              <Badge tone="success">{appointment[4]}</Badge>
              <p className="mt-2 flex items-center justify-end gap-2 text-sm font-semibold text-slate-700">
                <Clock className="h-4 w-4" />
                {appointment[0]}
              </p>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}

