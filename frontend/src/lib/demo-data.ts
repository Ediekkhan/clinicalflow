import type { ProviderSlot, Ticket } from '@/lib/types';

export const demoTickets: Ticket[] = [
  {
    id: '10000000-0000-4000-8000-000000000001',
    tenant_id: '00000000-0000-4000-8000-000000000001',
    ticket_number: 'SV-2026-9402',
    customer_phone: '+2348012345678',
    account_group_phone: '+2348012345678',
    channel: 'WHATSAPP',
    urgency_level: 'CRITICAL',
    matched_condition_id: 'acute_coronary_warning',
    assigned_specialty: 'Emergency Medicine',
    queue_status: 'QUEUED',
    is_manually_escalated: false,
    appointment_slot: null,
    raw_intake_text: 'Chest dey pain and breathing fast since morning.',
    extracted_symptoms: 'chest_pain,short_breath',
    created_at: new Date().toISOString(),
  },
  {
    id: '10000000-0000-4000-8000-000000000002',
    tenant_id: '00000000-0000-4000-8000-000000000001',
    ticket_number: 'SV-2026-9403',
    customer_phone: '+2348098765432',
    account_group_phone: '+2348098765432',
    channel: 'SMS',
    urgency_level: 'URGENT',
    matched_condition_id: 'pregnancy_abdominal_pain',
    assigned_specialty: 'Obstetrics',
    queue_status: 'QUEUED',
    is_manually_escalated: false,
    appointment_slot: null,
    raw_intake_text: 'Pregnant patient with belle pain.',
    extracted_symptoms: 'pregnancy_pain',
    created_at: new Date().toISOString(),
  },
  {
    id: '10000000-0000-4000-8000-000000000003',
    tenant_id: '00000000-0000-4000-8000-000000000001',
    ticket_number: 'SV-2026-9404',
    customer_phone: '+2348077772222',
    account_group_phone: '+2348077772222',
    channel: 'WEB',
    urgency_level: 'ROUTINE',
    matched_condition_id: 'febrile_illness',
    assigned_specialty: 'General Practice',
    queue_status: 'BEING_SEEN',
    is_manually_escalated: false,
    appointment_slot: null,
    raw_intake_text: 'Hot body and headache, started yesterday.',
    extracted_symptoms: 'fever,headache',
    created_at: new Date().toISOString(),
  },
];

const now = new Date();

export const demoSlots: ProviderSlot[] = Array.from({ length: 18 }).map((_, index) => {
  const starts = new Date(now);
  starts.setHours(8 + Math.floor(index / 3), (index % 3) * 20, 0, 0);
  const ends = new Date(starts.getTime() + 20 * 60 * 1000);
  const providers = [
    ['Dr. Ekanem', 'General Practice', 'Room 2'],
    ['Dr. Balogun', 'Emergency Medicine', 'Room 4'],
    ['Dr. Udo', 'Obstetrics', 'Room 3'],
  ] as const;
  const provider = providers[index % providers.length];
  return {
    id: `20000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
    tenant_id: '00000000-0000-4000-8000-000000000001',
    provider_name: provider[0],
    specialty: provider[1],
    room_label: provider[2],
    starts_at: starts.toISOString(),
    ends_at: ends.toISOString(),
    is_locked: index === 7,
    lock_reason: index === 7 ? 'Emergency theatre spillover' : null,
  };
});

