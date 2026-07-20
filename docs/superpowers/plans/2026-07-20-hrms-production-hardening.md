# AIVAN HRMS Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver secure and complete Phase 1 and Phase 2 HRMS workflows with repeatable production deployment, without visual UI changes.

**Architecture:** FastAPI owns authentication, role enforcement, state transitions, audit events, and database persistence. Angular retains existing screens and binds existing services to safe APIs. Docker Compose runs the SPA/Nginx, API, and PostgreSQL as separate services.

**Tech Stack:** Angular, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, Docker Compose, Nginx.

---

### Task 1: Secure employee credentials and activation

**Files:**
- Modify: `backend/app/services/employee_service.py`
- Modify: `backend/app/api/v1/employee_routes.py`
- Modify: `backend/app/schemas/employee.py`
- Create: `backend/tests/test_employee_activation_security.py`

- [ ] Write failing tests proving employee creation responses never contain a password and activation tokens are one-time.
- [ ] Add server-generated activation token storage, expiry, first-password setup, and safe response schemas.
- [ ] Run focused pytest tests, then the full backend suite.

### Task 2: Enforce attendance ownership and correction permissions

**Files:**
- Modify: `backend/app/api/v1/attendance_routes.py`
- Modify: `backend/app/services/attendance_service.py`
- Create: `backend/tests/test_attendance_authorization.py`

- [ ] Write failing tests proving an Employee cannot punch for another employee and HR/Admin correction requires an audit reason.
- [ ] Derive employee ownership from the JWT, add privileged correction endpoints, and record audits.
- [ ] Run focused pytest tests, then the full backend suite.

### Task 3: Activate and complete Time Off workflow

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/v1/timeoff_routes.py`
- Modify: `backend/app/services/timeoff_service.py`
- Modify: `backend/app/schemas/timeoff.py`
- Create: `backend/tests/test_timeoff_workflow.py`

- [ ] Write failing tests for Employee -> Manager -> HR approval, HR override, cancellation, balances, and authorization.
- [ ] Enable the router and implement state transitions, notifications, and audit records.
- [ ] Run focused pytest tests and full API suite.

### Task 4: Implement attendance regularization and master data guards

**Files:**
- Modify/create: `backend/app/models/*`, `backend/app/schemas/*`, `backend/app/api/v1/*`, `backend/app/services/*`
- Create: `backend/alembic/versions/*_regularization_and_audits.py`
- Create: `backend/tests/test_regularization_workflow.py`

- [ ] Write failing approval and recalculation tests.
- [ ] Add regularization entities, guarded state transitions, master-data reference validation, and migration.
- [ ] Run migrations against a disposable PostgreSQL database and full tests.

### Task 5: Harden API platform behavior

**Files:**
- Modify: `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/core/security.py`
- Modify: `backend/app/api/deps.py`, `backend/app/core/database.py`
- Create: `backend/tests/test_security_hardening.py`

- [ ] Add tests for required production settings, CORS allowlist, secure authentication responses, and role checks.
- [ ] Implement environment validation, structured/redacted logging, rate limiting, health checks, audit utilities, and lazy database setup.
- [ ] Run full backend tests.

### Task 6: Preserve UI and bind Phase 2 behavior safely

**Files:**
- Modify only existing service and component TypeScript files required for API integration.
- Test: existing Angular specs plus new service/component specs.

- [ ] Add failing tests for safe API error handling and completed Phase 2 service calls.
- [ ] Update service integration without changing HTML/CSS layout or visual components.
- [ ] Run Angular tests and production build.

### Task 7: Add production deployment assets

**Files:**
- Create: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.env.example`
- Create: `deploy/nginx/hrms.conf`, `deploy/scripts/backup-postgres.sh`, `deploy/scripts/deploy.sh`
- Create: `.github/workflows/ci.yml`, `docs/deployment/ubuntu-production-runbook.md`

- [ ] Build Compose images and run health checks locally/staging.
- [ ] Add migration, backup/restore, rollback, Nginx, HTTPS, firewall, and monitoring instructions.
- [ ] Deploy only after UAT and all tests pass.
