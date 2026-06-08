CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(160) NOT NULL,
  state_location VARCHAR(32) NOT NULL CHECK (state_location IN ('Akwa Ibom', 'Lagos')),
  status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staff (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role VARCHAR(24) NOT NULL CHECK (role IN ('ADMIN', 'NURSE', 'MATRON')),
  hashed_pin VARCHAR(255) NOT NULL,
  full_name VARCHAR(160) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  ticket_number VARCHAR(32) NOT NULL UNIQUE,
  customer_phone VARCHAR(32) NOT NULL,
  account_group_phone VARCHAR(32) NOT NULL,
  channel VARCHAR(20) NOT NULL CHECK (channel IN ('WHATSAPP', 'USSD', 'WEB', 'SMS')),
  urgency_level VARCHAR(20) NOT NULL CHECK (urgency_level IN ('CRITICAL', 'URGENT', 'ROUTINE')),
  matched_condition_id VARCHAR(80),
  assigned_specialty VARCHAR(120),
  queue_status VARCHAR(24) NOT NULL DEFAULT 'QUEUED' CHECK (queue_status IN ('QUEUED', 'BEING_SEEN', 'RESOLVED')),
  is_manually_escalated BOOLEAN NOT NULL DEFAULT FALSE,
  appointment_slot TIMESTAMPTZ,
  raw_intake_text TEXT,
  extracted_symptoms TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS provider_slots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider_name VARCHAR(160) NOT NULL,
  specialty VARCHAR(120) NOT NULL,
  room_label VARCHAR(40) NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  is_locked BOOLEAN NOT NULL DEFAULT FALSE,
  lock_reason VARCHAR(180)
);

CREATE TABLE IF NOT EXISTS appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  provider_slot_id UUID NOT NULL REFERENCES provider_slots(id) ON DELETE RESTRICT,
  status VARCHAR(24) NOT NULL DEFAULT 'BOOKED' CHECK (status IN ('BOOKED', 'CANCELLED', 'COMPLETED', 'NO_SHOW')),
  channel_origin VARCHAR(20) NOT NULL CHECK (channel_origin IN ('WHATSAPP', 'SMS', 'WEB', 'USSD')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_appointment_provider_slot UNIQUE (provider_slot_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  staff_id UUID REFERENCES staff(id) ON DELETE SET NULL,
  action VARCHAR(240) NOT NULL,
  ip_address INET,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_staff_tenant_role ON staff(tenant_id, role);
CREATE INDEX IF NOT EXISTS ix_tickets_tenant_queue ON tickets(tenant_id, queue_status, urgency_level);
CREATE INDEX IF NOT EXISTS ix_tickets_phone_active ON tickets(tenant_id, customer_phone, queue_status);
CREATE INDEX IF NOT EXISTS ix_provider_slots_tenant_starts ON provider_slots(tenant_id, starts_at);
CREATE INDEX IF NOT EXISTS ix_appointments_tenant_status ON appointments(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_time ON audit_logs(tenant_id, timestamp);

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_self_policy ON tenants;
CREATE POLICY tenant_self_policy ON tenants
  USING (id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON staff;
CREATE POLICY tenant_isolation_policy ON staff
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON tickets;
CREATE POLICY tenant_isolation_policy ON tickets
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON provider_slots;
CREATE POLICY tenant_isolation_policy ON provider_slots
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON appointments;
CREATE POLICY tenant_isolation_policy ON appointments
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation_policy ON audit_logs;
CREATE POLICY tenant_isolation_policy ON audit_logs
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

