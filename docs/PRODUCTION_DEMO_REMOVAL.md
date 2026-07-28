# Production Demo Removal

Status: verified backend cutover foundation, not deployment approval.

Implemented:

- Runtime demo account and schedule seeding is test-only.
- Shared PIN and hospital-code login are test-only.
- Static testimonial personas no longer populate the public API.
- Production configuration rejects unsafe demo, test, secret, SQLite, cookie, debug, and
  local-origin settings, default credentials, and the legacy universal demo tenant.
- Exact-identifier demo audit and dry-run cleanup commands are available.

Verification: focused authentication, migration, and startup-related suite passed with
18 focused backend tests on 2026-07-28.

The next required phase is real signup, OTP delivery, facility provisioning, and account
recovery. This repository must not be deployed as a real pilot until those workflows and
the controlled-pilot acceptance gates pass.
