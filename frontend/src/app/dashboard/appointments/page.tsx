import { redirect } from 'next/navigation';

export default function OldHospitalAppointmentsRedirect() {
  redirect('/hospital/appointments');
}

