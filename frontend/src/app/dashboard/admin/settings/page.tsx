import { redirect } from 'next/navigation';

export default function OldHospitalSettingsRedirect() {
  redirect('/hospital/admin/settings');
}

