# AIVAN HRMS Production Hardening Design

## Objective

Make the existing AIVAN HRMS Phase 1 and Phase 2 functionality safe, complete, deployable, and observable for production use without changing the current visual UI.

## Release Scope

- Phase 1: HR employee provisioning, secure account activation, authenticated employee dashboard, self-only attendance punching and history, HR attendance oversight.
- Phase 2: leave/time-off balances and requests, Employee -> Manager -> HR approval workflow, HR override, attendance regularization, notifications, master-data validation, and role-scoped reporting/export behavior.
- Platform: Docker Compose deployment with FastAPI, Angular/Nginx, PostgreSQL, environment-based configuration, migrations, backup/runbook guidance, and public HTTPS-ready reverse-proxy configuration.

## Constraints

- Preserve all current screen layouts, components, labels, and visual styling.
- Do not expose plaintext passwords, default passwords, tokens, or sensitive employee data in API responses, logs, or browser storage.
- Public production access requires HTTPS. HTTP can only be used for controlled internal staging.
- Leave approval is Employee -> Reporting Manager -> HR. HR can override/cancel with an audit reason.

## Architecture

The Angular application remains a single SPA and keeps its existing UI. It uses the existing API services, with no navigation or visual redesign. The FastAPI backend becomes the authorization boundary: it derives the effective employee from the authenticated user, enforces role permissions for sensitive actions, records audit events, and returns safe response payloads.

Time-off and regularization use explicit request state machines. Time-off moves from pending manager review to pending HR review, then approved/rejected/cancelled. Regularization requests are employee-created, manager-reviewed, and HR-finalized; attendance recalculation happens only after the approved state transition.

Production runs as Docker Compose services behind Nginx. PostgreSQL is private to the Docker network. FastAPI receives trusted proxy headers only from Nginx. Configuration comes from uncommitted environment files; no secrets are kept in source control.

## Security Decisions

- Attendance punch endpoints ignore caller-supplied employee IDs for Employee roles. HR/Admin corrective actions require an explicit privileged endpoint and reason.
- New users receive a server-generated, one-time activation token. The activation flow sets the first password; creation APIs return only delivery status, never credentials.
- JWT access tokens are short-lived. A server-side role check applies to all employee, attendance, leave, approval, report, and export operations.
- Passwords use bcrypt/passlib hashing. Login/reset endpoints are rate limited, CORS is allowlisted, and security headers are applied at Nginx.
- Audit logs record actor, action, target, timestamp, request source, and safe before/after values for sensitive changes.

## Testing Strategy

- Add backend regression tests for self-only attendance, role-based correction, credential-safe responses, activation tokens, time-off transitions, approval permissions, regularization, and report scoping.
- Retain frontend UI tests and add service-level tests where UI behavior changes without visual changes.
- Test Docker build, Alembic migration, health endpoints, and a production-like end-to-end smoke flow.

## Deployment Sequence

1. Complete code and automated tests in the isolated branch.
2. Run migrations and smoke tests in a staging Compose environment.
3. Install Docker, Nginx, and firewall configuration on the Ubuntu VM.
4. Deploy internally through VPN, complete HR UAT, and rotate shared VM credentials.
5. Configure DNS and HTTPS before public launch; keep port 80 only for redirect/certificate issuance.
