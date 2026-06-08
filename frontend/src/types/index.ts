export type UrgencyLevel = 'CRITICAL' | 'URGENT' | 'ROUTINE';
export type QueueStatus = 'QUEUED' | 'BEING_SEEN' | 'RESOLVED' | 'CANCELLED';
export type Gender = 'MALE' | 'FEMALE' | 'OTHER';

export type Patient = {
  id: string;
  tenant_id: string;
  full_name: string;
  phone: string;
  date_of_birth: string;
  gender: Gender;
  card_number: string;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
};

export type Specialist = {
  id: string;
  tenant_id: string;
  full_name: string;
  specialty: string;
  phone: string;
  email: string;
  is_available: boolean;
};

export type PatientTicket = {
  id: string;
  tenant_id: string;
  patient_id: string;
  ticket_number: string;
  symptom_description: string;
  extracted_symptom_ids: string[];
  matched_condition_id: string;
  matched_condition_name: string;
  assigned_specialty: string;
  urgency_level: UrgencyLevel;
  assigned_specialist_id: string;
  assigned_clinic_id: string;
  queue_status: QueueStatus;
  is_manually_escalated: boolean;
  appointment_slot: string;
  channel: 'WEB' | 'WHATSAPP' | 'SMS';
  created_at: string;
  patient_name: string;
  patient_card_number: string;
  wait_minutes: number;
  pendingSync?: boolean;
};

export type ClinicMatch = {
  clinic_name: string;
  address: string;
  distance_km: number;
  available_slots: number;
  specialist_name: string;
};

export type TriageResult = {
  ticket: PatientTicket;
  condition_name: string;
  urgency: UrgencyLevel;
  specialty: string;
  nearest_clinic: ClinicMatch;
  appointment_slot: {
    slot_start: string;
    slot_end: string;
    specialist_name: string;
    specialty: string;
  };
  severity_message: string;
};

export type SynNotification = {
  id: string;
  recipient_type: 'SPECIALIST' | 'PATIENT';
  recipient_id: string;
  title: string;
  body: string;
  is_read: boolean;
  ticket_id: string | null;
  urgency_level?: UrgencyLevel;
  patient_name?: string;
  condition_name?: string;
  created_at: string;
};

export type NetworkState = 'connected' | 'reconnecting' | 'offline';

