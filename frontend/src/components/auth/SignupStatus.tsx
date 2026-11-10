'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { CheckCircle2, Clock3, Loader2, ShieldAlert } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AuthFrame } from '@/components/auth/AuthFrame';
import { api } from '@/lib/auth';

type StatusResponse = { id: string; reference: string; application_type: string; status: string; login_path: string; dashboard_path?: string | null };
const statusCopy: Record<string, { title: string; body: string }> = {
  ACTIVE: { title: 'Account approved', body: 'Your account is active. Continue to your secure workspace.' },
  PHONE_VERIFICATION_REQUIRED: { title: 'Verify your phone', body: 'Enter the code sent to your verified phone number to activate the patient account.' },
  EMAIL_VERIFICATION_REQUIRED: { title: 'Verify your email', body: 'Enter the code sent to your email address.' },
  PENDING_EMPLOYER_APPROVAL: { title: 'Employer approval pending', body: 'Your organization must confirm your membership before clinical access is enabled.' },
  PENDING_HOSPITAL_APPROVAL: { title: 'Facility approval required', body: 'The selected facility must approve your staff membership.' },
  FACILITY_APPROVAL_REQUIRED: { title: 'Facility approval required', body: 'An authorized facility administrator must approve this membership.' },
  LICENCE_VERIFICATION_REQUIRED: { title: 'Licence verification required', body: 'Your professional registration requires verification before clinical access.' },
  MEMBERSHIP_ACTIVE: { title: 'Membership active', body: 'Your verified facility membership is active.' },
  MEMBERSHIP_SUSPENDED: { title: 'Membership suspended', body: 'Contact the facility administrator for review.' },
  INVITATION_EXPIRED: { title: 'Invitation expired', body: 'Ask the facility administrator to issue a new invitation.' },
  PENDING_PROFESSIONAL_VERIFICATION: { title: 'Professional verification pending', body: 'Credentials and organization membership are being reviewed.' },
  PENDING_FACILITY_VERIFICATION: { title: 'Facility verification pending', body: 'The organization, location and declared capabilities must be verified before activation.' },
  PENDING_PHARMACY_VERIFICATION: { title: 'Pharmacy verification pending', body: 'The premises and responsible professional must be verified before prescription access.' },
  PENDING_LABORATORY_VERIFICATION: { title: 'Laboratory verification pending', body: 'Accreditation and responsible staff must be verified before result access.' },
  PENDING_PAYER_VERIFICATION: { title: 'Payer verification pending', body: 'Regulatory and organization information is under review.' },
  PENDING_GOVERNMENT_VERIFICATION: { title: 'Agency verification pending', body: 'Requested reporting scope requires authorized agency review.' },
  PENDING_VERIFICATION: { title: 'Verification pending', body: 'Your application was submitted and is awaiting an authorized review.' },
  REJECTED: { title: 'Application not approved', body: 'Contact onboarding support for the available next steps.' },
  SUSPENDED: { title: 'Application suspended', body: 'This application is temporarily suspended. Contact onboarding support.' },
};

export function SignupStatus() {
  const search = useSearchParams();
  const router = useRouter();
  const id = search.get('id');
  const [application, setApplication] = useState<StatusResponse | null>(id ? { id, reference: search.get('reference') ?? '', application_type: '', status: search.get('status') ?? 'PENDING_VERIFICATION', login_path: '/login' } : null);
  const [loading, setLoading] = useState(Boolean(id));
  const [error, setError] = useState('');
  const [code, setCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    api.get(`/api/v1/signup/status/${id}`).then((data) => {
      if (cancelled) return;
      const next = data as StatusResponse;
      setApplication(next);
      if (next.status === 'ACTIVE' && next.dashboard_path) router.replace(next.dashboard_path);
    }).catch((caught) => { if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unable to load application status.'); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  async function verifyPhone() {
    if (!application || code.trim().length < 4) return;
    setVerifying(true);
    setError('');
    try {
      const verified = await api.post('/api/v1/signup/verify-phone', { application_id: application.id, code: code.trim() }) as StatusResponse;
      setApplication(verified);
      if (verified.status === 'ACTIVE' && verified.dashboard_path) router.replace(verified.dashboard_path);
    }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to verify this code.'); }
    finally { setVerifying(false); }
  }

  async function resendPhone() {
    if (!application) return;
    setResending(true);
    setError('');
    try {
      await api.post('/api/v1/signup/resend-phone', { application_id: application.id, code: '0000' });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to resend the verification code.');
    } finally {
      setResending(false);
    }
  }

  const copy = statusCopy[application?.status ?? 'PENDING_VERIFICATION'] ?? statusCopy.PENDING_VERIFICATION;
  const active = application?.status === 'ACTIVE';
  return (
    <AuthFrame eyebrow="Application status" title={copy.title} description={copy.body}>
      <div className="max-w-lg rounded-2xl border border-[#dbe2dc] bg-[#f8f9f5] p-6 sm:p-8">
        {loading ? <div className="flex items-center gap-3 text-sm font-bold text-[#60706a]"><Loader2 className="h-5 w-5 animate-spin" />Checking your application...</div> : <>
          <div className={`grid h-14 w-14 place-items-center rounded-full ${active ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{active ? <CheckCircle2 className="h-7 w-7" /> : application?.status === 'REJECTED' || application?.status === 'SUSPENDED' ? <ShieldAlert className="h-7 w-7" /> : <Clock3 className="h-7 w-7" />}</div>
          <p className="mt-6 text-xs font-bold uppercase tracking-wider text-[#60706a]">Application reference</p>
          <p className="mt-1 break-all font-mono text-lg font-bold text-[#10231e]">{application?.reference || 'Not available'}</p>
          <p className="mt-5 text-sm font-bold text-[#10231e]">Status: <span className="text-[#0b5d4b]">{application?.status?.replaceAll('_', ' ')}</span></p>
          {application?.status === 'PHONE_VERIFICATION_REQUIRED' ? <div className="mt-6 grid gap-3"><label className="grid gap-2 text-sm font-bold text-[#10231e]">Verification code<input value={code} onChange={(event) => setCode(event.target.value)} inputMode="numeric" autoComplete="one-time-code" className="min-h-12 rounded-xl border border-[#dbe2dc] bg-white px-4 outline-none focus:border-[#0b5d4b]" /></label><button type="button" onClick={() => void verifyPhone()} disabled={verifying || code.trim().length < 4} className="sv-button-dark w-full">{verifying ? 'Verifying...' : 'Verify and activate account'}</button><button type="button" onClick={() => void resendPhone()} disabled={resending} className="text-sm font-bold text-[#0b5d4b] disabled:opacity-50">{resending ? 'Sending...' : 'Resend verification code'}</button></div> : null}
          {error ? <p role="alert" className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p> : null}
          <div className="mt-7 grid gap-3 sm:grid-cols-2"><Link href="/signup" className="inline-flex min-h-12 items-center justify-center rounded-full border border-[#dbe2dc] bg-white px-4 text-sm font-bold text-[#10231e]">Workspace selection</Link><Link href={active && application?.dashboard_path ? application.dashboard_path : application?.login_path ?? '/login'} className="sv-button-dark">{active ? 'Open workspace' : 'Go to sign in'}</Link></div>
        </>}
      </div>
    </AuthFrame>
  );
}
