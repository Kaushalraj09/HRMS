# Phase 1 Master Implementation Document

## 1. What This Document Is For

This is the **master Phase 1 document** for the Aivan HRMS Portal.

This file is the combined overview for:

- product scope
- role flow
- current frontend status
- backend implementation direction
- Phase 1 API expectations
- execution order

This document is the overview file.

The detailed files are:

- [phase1 frontend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase1%20frontend.md)
- [phase1 backend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase1%20backend.md)

These 3 files together are now the only Phase 1 source of truth in the repo.

---

## 2. Phase 1 Goal

Build one shared HRMS portal where:

- `admin` can manage HR users and view employees
- `hr` can manage employees and attendance
- `employee` can access self-service dashboard and attendance

All users log in from the **same portal**.

---

## 3. Final Phase 1 Role Flow

### Admin Flow

1. Admin logs in
2. Admin lands on `Master Dashboard`
3. Admin can:
   - view admin summary cards
   - view HR users
   - create HR user
   - view employees

### HR Flow

1. HR logs in
2. HR lands on `HR Dashboard`
3. HR can:
   - view HR summary metrics
   - view employee attendance history
   - view employee list
   - create employee with login
   - open employee detail
   - edit employee

### Employee Flow

1. Employee logs in
2. Employee lands on `Employee Dashboard`
3. Employee can:
   - punch in / punch out
   - view today attendance state
   - view timesheets
   - view own profile
   - change password

---

## 4. Role Access Matrix

| Feature | Admin | HR | Employee |
|---|---|---|---|
| Login | Yes | Yes | Yes |
| Master Dashboard | Yes | No | No |
| HR Dashboard | Yes | Yes | No |
| HR User List | Yes | No | No |
| Create HR | Yes | No | No |
| Employee List | Yes | Yes | No |
| Add Employee | Yes | Yes | No |
| Edit Employee | Yes | Yes | No |
| Attendance History | Yes | Yes | No |
| Employee Dashboard | Optional | No | Yes |
| My Attendance | Optional | No | Yes |
| My Profile | Optional | No | Yes |
| Change Password | Optional | Optional | Yes |

---

## 5. Phase 1 Scope

### In Scope

- shared login page
- role-based route access
- admin dashboard
- HR dashboard
- employee dashboard
- admin HR list
- admin create HR
- admin employee list
- HR employee list
- HR add employee with login access
- HR employee detail/edit
- HR attendance history
- employee self attendance
- employee punch flow
- employee profile
- employee password change
- backend-ready service layer

### Out Of Scope

- payroll
- leave workflow
- client/project billing
- performance management
- mobile app
- biometric integration
- multi-company setup

---

## 6. Current Frontend Status

Frontend Phase 1 is already implemented in **mock backend-ready mode**.

This means:

- screens are implemented
- route flow is implemented
- role guards are implemented
- services are implemented
- browser-based local data store is implemented
- backend can now be developed against the same frontend contracts

### Current Frontend Source Files

- [app.routes.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/app.routes.ts)
- [auth.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/auth.service.ts)
- [employee.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/employee.service.ts)
- [attendance.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/attendance.service.ts)
- [dashboard.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/dashboard.service.ts)
- [hr.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/hr.service.ts)
- [profile.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/profile.service.ts)
- [phase1-store.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/phase1-store.service.ts)

### Current Frontend Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@aivan.com` | `Admin@123` |
| HR | `hr@aivan.com` | `Hr@12345` |
| Employee | `kaushal@aivan.com` | `Employee@123` |
| Employee | `ananya.employee@aivan.com` | `Employee@123` |
| Employee | `rahul@aivan.com` | `Employee@123` |

---

## 7. Current Screen Status Summary

### Updated Existing Screens

- Login
- Master Dashboard
- HR Dashboard
- HR Employee List
- Add Employee
- HR Attendance
- Employee Dashboard
- My Attendance
- My Profile
- Change Password
- Shared Sidebar
- Shared Dropdown
- HR Sidebar
- Employee Sidebar
- App Routes

### New Screens Added

- Admin HR Users
- Admin Create HR
- Admin Employees
- Employee Detail / Edit

For exact screen notes, use:

- [phase1 frontend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase1%20frontend.md)

---

## 8. Recommended Backend Architecture

For Phase 1, use:

- FastAPI backend
- PostgreSQL database
- JWT authentication
- modular monolith architecture

### Why

- simple to maintain
- beginner-friendly
- enough for current scale
- matches current frontend service structure well

### Backend Modules

- Auth Module
- HR Module
- Employee Module
- Attendance Module
- Dashboard Module
- Profile Module

For full backend breakdown, use:

- [phase1 backend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase1%20backend.md)

---

## 9. Phase 1 API Modules Needed

The frontend is waiting for these backend API groups:

### Auth APIs

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

### HR APIs

- `GET /api/v1/hr-users`
- `POST /api/v1/hr-users`

### Employee APIs

- `GET /api/v1/employees`
- `GET /api/v1/employees/{id}`
- `POST /api/v1/employees`
- `PUT /api/v1/employees/{id}`

### Attendance APIs

- `GET /api/v1/attendance`
- `GET /api/v1/attendance/me/timesheets`
- `GET /api/v1/attendance/me/today`
- `POST /api/v1/attendance/me/punch`
- `GET /api/v1/attendance/me/summary`

### Dashboard APIs

- `GET /api/v1/dashboard/admin`
- `GET /api/v1/dashboard/hr`

### Profile API

- `GET /api/v1/profile/me`

---

## 10. Recommended Backend Implementation Order

This is the best order for a fresher:

1. create backend project structure
2. configure database
3. create roles and users tables
4. implement login API
5. implement admin HR APIs
6. implement employee APIs
7. implement attendance APIs
8. implement dashboard APIs
9. implement profile and password APIs
10. connect frontend services one by one

Do not build everything together.

---

## 11. Frontend To Backend Integration Order

Once backend starts working, connect frontend in this order:

1. `AuthService`
2. `HrService`
3. `EmployeeService`
4. `AttendanceService`
5. `DashboardService`
6. `ProfileService`

Reason:

- login and role flow should work first
- then admin flow
- then HR flow
- then employee flow

---

## 12. Important Implementation Rules

### Rule 1

Keep one portal for all roles.

### Rule 2

Admin creates HR.

### Rule 3

HR creates employee with login in same flow.

### Rule 4

Employee sees only self data.

### Rule 5

Backend APIs must match existing frontend model shapes.

### Rule 6

Replace mock frontend services gradually, not all at once.

---

## 13. What Is Complete Today

Already complete:

- frontend role flow
- frontend protected routes
- frontend admin screens
- frontend HR screens
- frontend employee screens
- frontend mock state layer
- frontend service layer
- updated Phase 1 frontend guide
- updated Phase 1 backend guide

Still pending:

- backend implementation
- real API integration
- production auth/token flow

---

## 14. Canonical Phase 1 Document Set

These are now the only valid Phase 1 docs:

- [phase one.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase%20one.md)
- [phase1 frontend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase1%20frontend.md)
- [phase1 backend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1-documents/phase1%20backend.md)

The old root-level duplicates have been removed.

