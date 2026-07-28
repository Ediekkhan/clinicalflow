export type Channel = 'WHATSAPP' | 'USSD' | 'WEB' | 'SMS';
export type UrgencyLevel = 'CRITICAL' | 'URGENT' | 'ROUTINE';
export type QueueStatus = 'QUEUED' | 'BEING_SEEN' | 'RESOLVED' | 'AWAITING_CLINICAL_REVIEW' | 'SPECIALIST_UNAVAILABLE';
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
  version: number;
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
  is_booked: boolean;
};

export type Appointment = {
  id: string;
  tenant_id: string;
  ticket_id: string;
  slot_id: string;
  customer_phone: string;
  hospital_id?: string;
  department_id?: string | null;
  doctor_id?: string | null;
  staff_membership_id?: string | null;
  specialty_id?: string | null;
  urgency?: string | null;
  status: 'BOOKED' | 'CANCELLED' | 'COMPLETED' | 'AWAITING_CLINICAL_REVIEW' | 'SPECIALIST_UNAVAILABLE';
  provider_name: string;
  specialty: string;
  room_label: string;
  starts_at: string;
  ends_at: string;
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
export type HospitalPatient = {
  id: string;
  patient_name: string;
  card_number: string | null;
  ticket_number: string;
  arrival_time: string;
  urgency: UrgencyLevel;
  required_specialty: string | null;
  department: string | null;
  assigned_doctor: string;
  queue_status: QueueStatus;
  status: string;
  assignment_status: string;
  routing_distance_km: number | null;
  routing_reason: string | null;
  routing_status: string | null;
  acceptance_required: boolean;
  appointment_status: string | null;
  appointment_id: string | null;
};

export type HospitalSpecialist = {
  id: string;
  user_id: string;
  full_name: string;
  title: string;
  specialty: string | null;
  department: string;
  license_status: string;
  is_on_duty: boolean;
  availability: 'AVAILABLE' | 'WITH_PATIENT' | 'FULLY_BOOKED' | 'OFF_DUTY' | 'ON_LEAVE' | 'INACTIVE';
  next_available_slot: string | null;
  appointments_today: number;
  current_workload: number;
  maximum_capacity: number;
  room_label: string | null;
};

export type HospitalDepartment = {
  id: string;
  name: string;
  code: string;
  description: string | null;
  status: string;
  coordinator: string | null;
  total_doctors: number;
  available_doctors: number;
  specialists_on_duty: number;
  nurses_on_duty: number;
  patients_waiting: number;
  appointments_today: number;
  average_wait_time_minutes: number | null;
  capacity_status: string;
  available_doctors_list: HospitalSpecialist[];
};
