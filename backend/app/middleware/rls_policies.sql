-- SynaptiVerse tenant isolation policies.
-- Run as a migration/admin role, never as the restricted application role.

ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE specialists ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS patient_tenant_isolation ON patients;
CREATE POLICY patient_tenant_isolation ON patients
  USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    OR current_setting('app.auth_flow', true) = 'LOGIN'
  )
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS ticket_tenant_isolation ON tickets;
CREATE POLICY ticket_tenant_isolation ON tickets
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS appointment_tenant_isolation ON appointments;
CREATE POLICY appointment_tenant_isolation ON appointments
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS specialist_tenant_isolation ON specialists;
CREATE POLICY specialist_tenant_isolation ON specialists
  USING (
    tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    OR current_setting('app.auth_flow', true) = 'LOGIN'
  )
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

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

-- The application role must not have BYPASSRLS.
-- Provision its password from deployment secrets rather than hardcoding it here.
-- CREATE ROLE synaptiverse_app LOGIN PASSWORD '<from env>';
-- GRANT CONNECT ON DATABASE synaptiverse TO synaptiverse_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO synaptiverse_app;
-- REVOKE UPDATE, DELETE ON audit_logs FROM synaptiverse_app;
-- GRANT INSERT, SELECT ON audit_logs TO synaptiverse_app;

