ALTER TABLE staff
  ADD COLUMN IF NOT EXISTS failed_pin_attempts INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;

ALTER TABLE patients
  ADD COLUMN IF NOT EXISTS pending_deletion BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE audit_logs
  ALTER COLUMN tenant_id DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS resource_type VARCHAR(30),
  ADD COLUMN IF NOT EXISTS resource_id UUID,
  ADD COLUMN IF NOT EXISTS user_agent TEXT;

ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_actor_type_check;
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_logs_actor_type;
ALTER TABLE audit_logs ADD CONSTRAINT ck_audit_logs_actor_type
  CHECK (actor_type IN ('PATIENT', 'SPECIALIST', 'STAFF', 'ADMIN', 'SYSTEM') OR actor_type IS NULL);

CREATE INDEX IF NOT EXISTS audit_actor_idx ON audit_logs (actor_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS audit_tenant_idx ON audit_logs (tenant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS audit_action_idx ON audit_logs (action, timestamp DESC);
CREATE INDEX IF NOT EXISTS audit_resource_idx ON audit_logs (resource_type, resource_id);

ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE specialists ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON patients;
DROP POLICY IF EXISTS patient_tenant_isolation ON patients;
CREATE POLICY patient_tenant_isolation ON patients
  USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    OR current_setting('app.auth_flow', true) = 'LOGIN'
  )
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS tenant_isolation_policy ON tickets;
DROP POLICY IF EXISTS ticket_tenant_isolation ON tickets;
CREATE POLICY ticket_tenant_isolation ON tickets
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS tenant_isolation_policy ON appointments;
DROP POLICY IF EXISTS appointment_tenant_isolation ON appointments;
CREATE POLICY appointment_tenant_isolation ON appointments
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS tenant_isolation_policy ON specialists;
DROP POLICY IF EXISTS specialist_tenant_isolation ON specialists;
CREATE POLICY specialist_tenant_isolation ON specialists
  USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    OR current_setting('app.auth_flow', true) = 'LOGIN'
  )
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS tenant_isolation_policy ON audit_logs;
DROP POLICY IF EXISTS auditlog_tenant_isolation ON audit_logs;
CREATE POLICY auditlog_tenant_isolation ON audit_logs
  USING (
    tenant_id IS NULL
    OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
  )
  WITH CHECK (
    tenant_id IS NULL
    OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
  );

DROP POLICY IF EXISTS tenant_isolation_policy ON notifications;
DROP POLICY IF EXISTS notification_tenant_isolation ON notifications;
CREATE POLICY notification_tenant_isolation ON notifications
  USING (
    (recipient_type = 'SPECIALIST' AND recipient_id IN (
      SELECT id FROM specialists
      WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    ))
    OR
    (recipient_type = 'PATIENT' AND recipient_id IN (
      SELECT id FROM patients
      WHERE tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    ))
  )
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS tenant_public_active_read ON tenants;
CREATE POLICY tenant_public_active_read ON tenants
  FOR SELECT
  USING (status = 'ACTIVE' OR id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- Grant pattern for production provisioning:
-- REVOKE UPDATE, DELETE ON audit_logs FROM synaptiverse_app;
-- GRANT INSERT, SELECT ON audit_logs TO synaptiverse_app;

