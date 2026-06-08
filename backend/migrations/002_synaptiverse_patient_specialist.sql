ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS address TEXT,
  ADD COLUMN IF NOT EXISTS latitude DECIMAL(9,6),
  ADD COLUMN IF NOT EXISTS longitude DECIMAL(9,6);

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS ck_tenants_state;
ALTER TABLE tenants ADD CONSTRAINT ck_tenants_state
  CHECK (state_location IN ('Akwa Ibom', 'Lagos', 'Rivers', 'FCT'));

CREATE TABLE IF NOT EXISTS patients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  full_name VARCHAR(160) NOT NULL,
  phone VARCHAR(32) NOT NULL,
  date_of_birth DATE,
  gender VARCHAR(12) CHECK (gender IN ('MALE', 'FEMALE', 'OTHER')),
  card_number VARCHAR(32) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS specialists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  full_name VARCHAR(160) NOT NULL,
  specialty VARCHAR(120) NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  phone VARCHAR(32),
  email VARCHAR(160) UNIQUE,
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE tickets
  ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS symptom_description TEXT,
  ADD COLUMN IF NOT EXISTS extracted_symptom_ids TEXT[],
  ADD COLUMN IF NOT EXISTS matched_condition_name VARCHAR(160),
  ADD COLUMN IF NOT EXISTS assigned_specialist_id UUID REFERENCES specialists(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS assigned_clinic_id UUID REFERENCES tenants(id) ON DELETE SET NULL;

ALTER TABLE tickets ALTER COLUMN customer_phone DROP NOT NULL;
ALTER TABLE tickets ALTER COLUMN account_group_phone DROP NOT NULL;
ALTER TABLE tickets DROP CONSTRAINT IF EXISTS ck_ticket_queue;
ALTER TABLE tickets ADD CONSTRAINT ck_ticket_queue
  CHECK (queue_status IN ('QUEUED', 'BEING_SEEN', 'RESOLVED', 'CANCELLED'));

ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS specialist_id UUID REFERENCES specialists(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS clinic_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS slot_start TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS slot_end TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS notes TEXT;

ALTER TABLE appointments ALTER COLUMN provider_slot_id DROP NOT NULL;
ALTER TABLE appointments ALTER COLUMN channel_origin DROP NOT NULL;
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS ck_appointments_status;
ALTER TABLE appointments ADD CONSTRAINT ck_appointments_status
  CHECK (status IN ('BOOKED', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW'));

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  recipient_type VARCHAR(24) NOT NULL CHECK (recipient_type IN ('SPECIALIST', 'PATIENT')),
  recipient_id UUID NOT NULL,
  title VARCHAR(180) NOT NULL,
  body TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS actor_id UUID,
  ADD COLUMN IF NOT EXISTS actor_type VARCHAR(24) CHECK (actor_type IN ('PATIENT', 'SPECIALIST', 'ADMIN', 'SYSTEM')),
  ADD COLUMN IF NOT EXISTS metadata JSONB;

CREATE INDEX IF NOT EXISTS ix_patients_tenant_phone ON patients(tenant_id, phone);
CREATE INDEX IF NOT EXISTS ix_specialists_tenant_specialty ON specialists(tenant_id, specialty);
CREATE INDEX IF NOT EXISTS ix_notifications_recipient ON notifications(tenant_id, recipient_type, recipient_id, is_read);

ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE specialists ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON patients;
CREATE POLICY tenant_isolation_policy ON patients
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON specialists;
CREATE POLICY tenant_isolation_policy ON specialists
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON notifications;
CREATE POLICY tenant_isolation_policy ON notifications
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

