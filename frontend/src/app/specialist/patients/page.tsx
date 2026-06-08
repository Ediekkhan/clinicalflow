import { redirect } from 'next/navigation';

export default function SpecialistPatientsRedirect() {
  redirect('/hospital/doctor/patients');
}

