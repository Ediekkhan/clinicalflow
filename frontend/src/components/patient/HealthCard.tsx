'use client';

import Image from 'next/image';
import { useEffect, useRef, useState, type MouseEvent } from 'react';
import { Check, Copy, Download, Pencil, RefreshCw, Share2, ShieldCheck, X } from 'lucide-react';
import QRCode from 'qrcode';
import { api } from '@/lib/auth';

type CurrentUser = {
  id?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  card_number?: string;
  date_of_birth?: string;
  gender?: string;
  state?: string;
  lga?: string;
  created_at?: string;
  card_valid_from?: string;
  card_valid_until?: string;
  blood_group?: string;
  genotype?: string;
  known_allergies?: string;
  emergency_contact?: string;
  hmo_provider?: string;
  locked_fields?: string[];
};

type CardField = 'blood_group' | 'genotype' | 'known_allergies' | 'emergency_contact' | 'hmo_provider';

type CardDetails = Record<CardField, string>;

type SecureCardCredential = {
  issuer?: string;
  expires_at?: string;
  emergency_access_enabled: boolean;
  qr_payload: string;
};

const detailFields: { field: CardField; label: string; empty: string; inputType?: string }[] = [
  { field: 'blood_group', label: 'Blood Group', empty: 'Not set' },
  { field: 'genotype', label: 'Genotype', empty: 'Not set' },
  { field: 'known_allergies', label: 'Known Allergies', empty: 'None recorded' },
  { field: 'emergency_contact', label: 'Emergency Contact', empty: 'Not set', inputType: 'tel' },
  { field: 'hmo_provider', label: 'HMO Provider', empty: 'Not enrolled' },
];

function formatDate(value?: string) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric' }).format(date);
}

function initials(user: CurrentUser | null) {
  const name = fullName(user);
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

function fullName(user: CurrentUser | null) {
  if (!user) return '';
  return user.full_name ?? [user.first_name, user.last_name].filter(Boolean).join(' ');
}

function displayGender(value?: string) {
  if (!value) return '';
  const normalized = value.toUpperCase();
  if (normalized === 'MALE') return 'M';
  if (normalized === 'FEMALE') return 'F';
  return value;
}

function location(user: CurrentUser | null) {
  return [user?.state, user?.lga].filter(Boolean).join(', ');
}

function emptyDetails(user: CurrentUser | null): CardDetails {
  return {
    blood_group: user?.blood_group ?? '',
    genotype: user?.genotype ?? '',
    known_allergies: user?.known_allergies ?? '',
    emergency_contact: user?.emergency_contact ?? '',
    hmo_provider: user?.hmo_provider ?? '',
  };
}

export function HealthCard() {
  const cardRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [cardDetails, setCardDetails] = useState<CardDetails>(emptyDetails(null));
  const [editingField, setEditingField] = useState<CardField | null>(null);
  const [editValue, setEditValue] = useState('');
  const [confirmField, setConfirmField] = useState<CardField | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [secureCredential, setSecureCredential] = useState<SecureCardCredential | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function loadUser() {
      try {
        const [data, credential] = await Promise.all([
          api.get('/api/v1/auth/patient/me') as Promise<CurrentUser>,
          api.get('/api/v1/patient/health-card') as Promise<SecureCardCredential>,
        ]);
        if (cancelled) return;
        setCurrentUser(data);
        setCardDetails(emptyDetails(data));
        setSecureCredential(credential);
        setQrDataUrl(await QRCode.toDataURL(credential.qr_payload, { width: 240, margin: 1, errorCorrectionLevel: 'H' }));
      } catch (error) {
        console.error(error);
        if (!cancelled) setCurrentUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadUser();
    return () => {
      cancelled = true;
    };
  }, []);

  const lockedFields = currentUser?.locked_fields ?? [];
  const name = fullName(currentUser);
  const cardNumber = currentUser?.card_number ?? '';
  const patientLocation = location(currentUser);

  function isLocked(field: CardField) {
    if (field === 'emergency_contact') return false;
    return lockedFields.includes(field);
  }

  function handleMove(event: MouseEvent<HTMLDivElement>) {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const rotateY = (x / rect.width - 0.5) * 8;
    const rotateX = (y / rect.height - 0.5) * -8;

    card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  }

  function resetTilt() {
    if (cardRef.current) {
      cardRef.current.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg)';
    }
  }

  async function copyCardNumber() {
    if (!cardNumber) return;
    try {
      await navigator.clipboard?.writeText(cardNumber);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  async function shareCard() {
    if (navigator.share && cardNumber) {
      await navigator.share({
        title: 'ClinicalFlow Health Card',
        text: [name, cardNumber].filter(Boolean).join(' - '),
      });
      return;
    }

    await copyCardNumber();
  }

  function handleEdit(field: CardField) {
    setEditingField(field);
    setEditValue(cardDetails[field] ?? '');
  }

  async function saveField(field: CardField) {
    setIsSaving(true);
    try {
      const updated = (await api.patch('/api/v1/patient/card-details', { [field]: editValue })) as CurrentUser;
      setCurrentUser((current) => ({ ...current, ...updated }));
      setCardDetails((current) => ({ ...current, [field]: editValue }));
      setEditingField(null);
      setConfirmField(null);
    } catch (error) {
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  }

  function requestSave(field: CardField) {
    if (field === 'emergency_contact') {
      void saveField(field);
      return;
    }
    setConfirmField(field);
  }

  const actions = [
    { label: 'Save to Photos', icon: Download, onClick: () => window.print() },
    { label: 'Share Card', icon: Share2, onClick: shareCard },
    { label: 'Refresh Card', icon: RefreshCw, onClick: () => window.location.reload() },
  ];

  if (isLoading) {
    return <div className="h-96 animate-pulse rounded-3xl bg-slate-100" />;
  }

  return (
    <div className="mx-auto grid w-full max-w-5xl gap-5">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-stretch">
        <div className="rounded-3xl border border-blue-100 bg-white p-3 shadow-sm sm:p-5">
          <div
            ref={cardRef}
            onMouseMove={handleMove}
            onMouseLeave={resetTilt}
            className="relative mx-auto aspect-[1.586] w-full max-w-[560px] overflow-hidden rounded-[1.35rem] border border-blue-400/40 bg-gradient-to-br from-[#10231e] via-[#1D2464] to-[#0b5d4b] p-4 text-white shadow-[0_24px_70px_rgba(37,99,235,0.25)] transition-transform duration-200 sm:p-6"
          >
            <div className="absolute -right-10 -top-12 h-36 w-36 rounded-full bg-blue-300/15 sm:h-44 sm:w-44" />
            <div className="absolute -bottom-16 -left-12 h-40 w-40 rounded-full bg-white/10" />
            <div className="absolute inset-x-6 top-20 h-px bg-white/15" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.12),transparent_24%),radial-gradient(circle_at_86%_18%,rgba(147,197,253,0.2),transparent_22%)]" />

            <div className="relative z-10 flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-blue-100 sm:text-xs">
                  ClinicalFlow Health Card
                </p>
                <p className="mt-1 text-xs font-semibold text-blue-100/80">Nigeria</p>
              </div>
              <div className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold">NG</div>
            </div>

            <button
              type="button"
              onClick={copyCardNumber}
              className="relative z-10 mt-8 block max-w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-left font-mono text-sm tracking-[0.14em] text-blue-100 backdrop-blur transition hover:bg-white/15 sm:mt-12 sm:text-base"
            >
              <span className="block break-all">{cardNumber}</span>
              {cardNumber ? (
                <span className="mt-1 flex items-center gap-1 text-[10px] font-semibold tracking-normal text-blue-100/70">
                  {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  {copied ? 'Copied' : 'Tap to copy'}
                </span>
              ) : null}
            </button>

            <div className="relative z-10 mt-5 sm:mt-8">
              <p className="font-display text-2xl leading-tight sm:text-4xl">{name}</p>
              <p className="mt-2 text-xs font-semibold text-blue-100/80 sm:text-sm">
                {[currentUser?.date_of_birth ? `DOB: ${formatDate(currentUser.date_of_birth)}` : '', displayGender(currentUser?.gender), patientLocation].filter(Boolean).join(' - ')}
              </p>
            </div>

            <div className="absolute bottom-4 left-4 right-4 z-10 grid gap-2 text-[10px] text-blue-100/80 sm:bottom-6 sm:left-6 sm:right-6 sm:grid-cols-[1fr_auto] sm:text-xs">
              <div className="grid gap-1 sm:grid-cols-3">
                <p>
                  <span className="text-white/50">VALID</span> {formatDate(currentUser?.card_valid_until)}
                </p>
                <p>
                  <span className="text-white/50">STATE</span> {currentUser?.state ?? ''}
                </p>
                <p>
                  <span className="text-white/50">TYPE</span> Patient
                </p>
              </div>
              <div className="inline-flex w-fit items-center gap-1 rounded-full bg-white/12 px-2 py-1 font-semibold text-white">
                <ShieldCheck className="h-3.5 w-3.5" />
                Verified
              </div>
            </div>
          </div>
        </div>

        <aside className="rounded-3xl border border-slate-100 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-900">Card actions</h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Keep your health identity ready for partner facilities.
          </p>

          <div className="mt-5 grid gap-3">
            {actions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.label}
                  type="button"
                  onClick={action.onClick}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-[#0b5d4b] hover:text-[#0b5d4b]"
                >
                  <Icon className="h-4 w-4" />
                  {action.label}
                </button>
              );
            })}
          </div>

          <div className="mt-5 rounded-2xl bg-blue-50 p-4 text-sm leading-6 text-blue-900">
            {qrDataUrl ? (
              <div className="flex flex-col items-center text-center">
                {/* The QR encodes an opaque, revocable lookup token; it contains no medical data. */}
                <Image src={qrDataUrl} alt="Secure health card lookup QR code" width={144} height={144} unoptimized className="h-36 w-36 rounded-lg bg-white p-2" />
                <p className="mt-3 font-semibold">Secure facility lookup</p>
                <p className="mt-1 text-xs text-blue-700">
                  {secureCredential?.issuer ? `Issued by ${secureCredential.issuer}. ` : ''}
                  Expires {formatDate(secureCredential?.expires_at)}.
                </p>
              </div>
            ) : (
              <p>Secure card lookup is currently unavailable.</p>
            )}
          </div>
        </aside>
      </div>

      <section className="rounded-3xl border border-slate-100 bg-white p-5 shadow-sm">
        <h3 className="font-semibold text-slate-900">Card Details</h3>
        <div className="mt-4 divide-y divide-slate-100">
          {detailFields.map(({ field, label, empty, inputType }) => {
            const locked = isLocked(field);
            const value = cardDetails[field];
            const editing = editingField === field;
            return (
              <div key={field} className="flex items-center justify-between gap-4 py-3">
                <span className="text-sm text-slate-500">{label}</span>
                {locked ? (
                  <span className="text-sm font-medium text-slate-900">{value || empty}</span>
                ) : (
                  <div className="flex items-center gap-2">
                    {editing ? (
                      <input
                        type={inputType ?? 'text'}
                        value={editValue}
                        onChange={(event) => setEditValue(event.target.value)}
                        placeholder={field === 'emergency_contact' ? '+234 XXX XXX XXXX' : undefined}
                        className="min-h-10 rounded-lg border border-emerald-400 px-2 py-1 text-sm outline-none"
                        autoFocus
                      />
                    ) : (
                      <span className="text-sm text-slate-900">{value || empty}</span>
                    )}
                    {editing ? (
                      <>
                        <button type="button" disabled={isSaving} onClick={() => requestSave(field)} className="rounded-lg bg-[#0D7A5F] px-3 py-2 text-xs font-semibold text-white disabled:bg-slate-300">
                          Save
                        </button>
                        <button type="button" onClick={() => setEditingField(null)} className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-500">
                          <X className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <button type="button" onClick={() => handleEdit(field)} className="grid h-9 w-9 place-items-center rounded-lg text-slate-400 hover:text-[#0D7A5F]" aria-label={`Edit ${label}`}>
                        <Pencil className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {confirmField ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Once saved, this cannot be changed.</h3>
            <p className="mt-2 text-sm text-slate-500">Are you sure?</p>
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" onClick={() => setConfirmField(null)} className="rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600">
                Cancel
              </button>
              <button type="button" disabled={isSaving} onClick={() => void saveField(confirmField)} className="rounded-xl bg-[#0D7A5F] px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-300">
                Confirm
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
