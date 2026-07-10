export type Channel = 'WHATSAPP' | 'USSD' | 'WEB' | 'SMS';
export type UrgencyLevel = 'CRITICAL' | 'URGENT' | 'ROUTINE';
export type QueueStatus = 'QUEUED' | 'BEING_SEEN' | 'RESOLVED';
export type NetworkMode = 'connected' | 'reconnecting' | 'offline';

export type Ticket = {
  id: string;
  tenant_id: string;
  ticket_number: string;
  customer_phone: string;
  account_group_phone: string;
  channel: Channel;
  urgency_level: UrgencyLevel;
  matched_condition_id: string | null;
  assigned_specialty: string | null;
  queue_status: QueueStatus;
  is_manually_escalated: boolean;
  appointment_slot: string | null;
  raw_intake_text: string | null;
  extracted_symptoms: string | null;
  created_at: string;
  pendingSync?: boolean;
  pulse?: boolean;
};

export type ProviderSlot = {
  id: string;
  tenant_id: string;
  provider_name: string;
  specialty: string;
  room_label: string;
  starts_at: string;
  ends_at: string;
  is_locked: boolean;
  lock_reason: string | null;
};

export type WebSocketEvent =
  | {
      type: 'ticket.created' | 'ticket.updated' | 'ticket.escalated';
      tenant_id: string;
      payload: Ticket;
      priority: 'LOW' | 'NORMAL' | 'HIGH';
    }
  | {
      type: 'appointment.updated' | 'system.notice';
      tenant_id: string;
      payload: Record<string, unknown>;
      priority: 'LOW' | 'NORMAL' | 'HIGH';
    };


export const urgencyMeta: Record<
  UrgencyLevel,
  { label: string; heading: string; fill: string; text: string; border: string }
> = {
  CRITICAL: {
    label: 'Critical',
    heading: 'Emergency',
    fill: 'bg-rose-50',
    text: 'text-rose-600',
    border: 'border-rose-200',
  },
  URGENT: {
    label: 'Urgent',
    heading: 'Delayed Care',
    fill: 'bg-amber-50',
    text: 'text-amber-600',
    border: 'border-amber-200',
  },
  ROUTINE: {
    label: 'Routine',
    heading: 'Standard Care',
    fill: 'bg-blue-50',
    text: 'text-blue-600',
    border: 'border-blue-200',
  },
};


