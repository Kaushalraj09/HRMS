# Phase 1 Frontend Implementation Guide

## 1. What This Document Is For

This document is the **updated Phase 1 frontend implementation guide** for the Aivan HRMS Portal.

This file is now aligned with the **actual frontend that is already implemented** in the repo.

It is written in a practical way so that a fresher developer can understand:

- what has already been completed
- which screens exist
- how the current frontend is structured
- how role flow works
- how the frontend will connect to backend later

This is now the correct Phase 1 frontend reference.

---

## 2. Phase 1 Frontend Scope

Phase 1 frontend supports 3 roles in one portal:

- `admin`
- `hr`
- `employee`

### Admin Flow

- login
- view admin dashboard
- view HR users
- create HR user
- view employee list

### HR Flow

- login
- view HR dashboard
- view employee list
- create employee with login access
- view employee detail
- edit employee
- view attendance history

### Employee Flow

- login
- view employee dashboard
- punch in / punch out
- view own attendance
- view own profile
- change password

---

## 3. Current Frontend Status

Phase 1 frontend is already implemented in **mock backend-ready mode**.

That means:

- UI is implemented
- role flow is implemented
- route protection is implemented
- services are implemented
- a browser-based local store is working as a temporary mock backend
- real backend APIs can be connected later without changing screen flow

### Important Note

The frontend currently uses:

- `Phase1StoreService`

This is a temporary browser-side data engine that behaves like a backend.

When backend is ready, frontend services should stop calling the store directly and should start calling real APIs using `HttpClient`.

---

## 4. Current Frontend Folder Structure

This is the real structure now used by the app:

```text
frontend/
└── src/
    └── app/
        ├── app.routes.ts
        ├── core/
        │   ├── guards/
        │   │   ├── auth.guard.ts
        │   │   └── role.guard.ts
        │   ├── models/
        │   │   ├── auth.model.ts
        │   │   ├── attendance.model.ts
        │   │   ├── dashboard.model.ts
        │   │   ├── employee.model.ts
        │   │   ├── hr.model.ts
        │   │   └── profile.model.ts
        │   └── services/
        │       ├── auth.service.ts
        │       ├── attendance.service.ts
        │       ├── dashboard.service.ts
        │       ├── employee.service.ts
        │       ├── hr.service.ts
        │       ├── phase1-store.service.ts
        │       └── profile.service.ts
        ├── features/
        │   ├── admin/
        │   │   └── pages/
        │   │       ├── add-hr/
        │   │       ├── admin-employees/
        │   │       └── hr-users/
        │   ├── auth/
        │   │   └── pages/
        │   │       ├── forgot-password/
        │   │       └── login/
        │   ├── emp/
        │   │   ├── components/
        │   │   │   └── emp-sidebar/
        │   │   └── pages/
        │   │       ├── change-password/
        │   │       ├── emp-dashboard/
        │   │       ├── my-attendance/
        │   │       └── my-profile/
        │   ├── hr/
        │   │   ├── components/
        │   │   │   └── hr-sidebar/
        │   │   └── pages/
        │   │       ├── attendance/
        │   │       ├── employees/
        │   │       │   ├── add-employee/
        │   │       │   ├── employee-detail/
        │   │       │   └── employees.ts/html/css
        │   │       └── hr-dashboard/
        │   └── master-dashboard/
        └── shared/
            └── components/
                ├── dropdown/
                ├── navbar/
                ├── sidebar/
                └── custom-select/
```

---

## 5. Actual Route Structure

The route structure is now defined in:

- [app.routes.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/app.routes.ts)

### Current Route Map

| Path | Role Access | Purpose |
|---|---|---|
| `/auth/login` | public | login |
| `/auth/forgot-password` | public | forgot password |
| `/master-dashboard` | admin | admin dashboard |
| `/master-dashboard/hr-users` | admin | HR user list |
| `/master-dashboard/hr-users/add` | admin | create HR |
| `/master-dashboard/employees` | admin | employee list |
| `/hr-dashboard` | admin, hr | HR dashboard |
| `/hr-dashboard/attendance` | admin, hr | HR attendance page |
| `/hr-dashboard/employees` | admin, hr | employee list |
| `/hr-dashboard/employees/add` | admin, hr | add employee |
| `/hr-dashboard/employees/:employeeId` | admin, hr | employee detail/edit |
| `/emp-dashboard` | admin, employee | employee dashboard |
| `/emp-dashboard/my-attendance` | admin, employee | employee attendance |
| `/emp-dashboard/my-profile` | admin, employee | employee profile |
| `/emp-dashboard/change-password` | admin, employee | employee password change |

### Guard Rules

Two guards are already created:

- [auth.guard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/guards/auth.guard.ts)
- [role.guard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/guards/role.guard.ts)

### Redirect Flow

- `admin` -> `/master-dashboard`
- `hr` -> `/hr-dashboard`
- `employee` -> `/emp-dashboard`

---

## 6. Current Role Flow

### Admin

1. Admin logs in
2. Admin lands on master dashboard
3. Admin can:
   - view summary cards
   - view HR users
   - create HR
   - view employees

### HR

1. HR logs in
2. HR lands on HR dashboard
3. HR can:
   - view HR summary metrics
   - view attendance history
   - open employee list
   - add employee
   - open employee detail
   - edit employee

### Employee

1. Employee logs in
2. Employee lands on employee dashboard
3. Employee can:
   - punch in / punch out
   - view today summary
   - view timesheets
   - view attendance page
   - view profile
   - change password

---

## 7. Current Implemented Screens

### 7.1 Updated Existing Screens

1. `Login page`  
   Updated to use Phase 1 mock auth flow and seeded credentials.  
   [login.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/auth/pages/login/login.ts)

2. `Master/Admin Dashboard`  
   Updated to show Phase 1 admin cards, HR users, and employee summaries.  
   [master-dashboard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/master-dashboard/master-dashboard.ts)

3. `HR Dashboard`  
   Updated to show dashboard cards, attendance metrics, work mode breakdown, and summary data.  
   [hr-dashboard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr/pages/hr-dashboard/hr-dashboard.ts)

4. `HR Employee List`  
   Updated for HR/Admin usage and linked to employee detail.  
   [employees.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr/pages/employees/employees.ts)

5. `Add Employee`  
   Updated to include account access and login creation fields in the same form.  
   [add-employee.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr/pages/employees/add-employee/add-employee.ts)

6. `HR Attendance`  
   Updated to use real Phase 1 filter flow.  
   [attendance.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr/pages/attendance/attendance.ts)

7. `Employee Dashboard`  
   Updated to support punch flow, summary, timesheet data, and mock dashboard logic.  
   [emp-dashboard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp/pages/emp-dashboard/emp-dashboard.ts)

8. `My Attendance`  
   Updated to support filtering by date and status.  
   [my-attendance.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp/pages/my-attendance/my-attendance.ts)

9. `My Profile`  
   Updated to read employee profile from store-backed service.  
   [my-profile.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp/pages/my-profile/my-profile.ts)

10. `Change Password`  
   Updated to work with Phase 1 password flow.  
   [change-password.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp/pages/change-password/change-password.service.ts)

11. `Shared Sidebar`  
   Updated for admin Phase 1 navigation.  
   [sidebar.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/shared/components/sidebar/sidebar.ts)

12. `Shared Dropdown`  
   Updated for role-aware profile link and logout behavior.  
   [dropdown.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/shared/components/dropdown/dropdown.ts)

13. `HR Sidebar`  
   Updated to use auth-based logout.  
   [hr-sidebar.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr/components/hr-sidebar/hr-sidebar.ts)

14. `Employee Sidebar`  
   Updated to use auth-based logout.  
   [emp-sidebar.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp/components/emp-sidebar/emp-sidebar.ts)

15. `App Routes`  
   Updated to include full Phase 1 route structure and role guards.  
   [app.routes.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/app.routes.ts)

### 7.2 New Screens Created

1. `Admin HR Users List`  
   [hr-users.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/admin/pages/hr-users/hr-users.ts)

2. `Admin Create HR`  
   [add-hr.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/admin/pages/add-hr/add-hr.ts)

3. `Admin Employees Page`  
   [admin-employees.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/admin/pages/admin-employees/admin-employees.ts)

4. `Employee Detail / Edit`  
   [employee-detail.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr/pages/employees/employee-detail/employee-detail.ts)

---

## 8. Current Frontend Data Models

These are the actual frontend models now in use.

### Auth Model

- [auth.model.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/models/auth.model.ts)

Main types:

- `UserRole`
- `LoginRequest`
- `SessionUser`
- `LoginResponse`
- `ChangePasswordPayload`

### Employee Model

- [employee.model.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/models/employee.model.ts)

Main types:

- `Employee`
- `PaginatedResult<T>`
- `EmployeePayload`
- `EmployeeDetailView`

### Attendance Model

- [attendance.model.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/models/attendance.model.ts)

Main types:

- `AttendanceRecord`
- `AttendanceMetrics`
- `PaginatedAttendance`
- `EmployeeTimesheetRow`
- `TodayAttendanceState`

### HR Model

- [hr.model.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/models/hr.model.ts)

Main types:

- `HrUser`
- `CreateHrPayload`

### Dashboard Model

- [dashboard.model.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/models/dashboard.model.ts)

Main types:

- `AdminDashboardData`
- `HrDashboardData`

### Profile Model

- [profile.model.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/models/profile.model.ts)

Main type:

- `EmployeeProfile`

---

## 9. Current Frontend Services

These services are already created and working in mock mode.

### Auth Service

- [auth.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/auth.service.ts)

Current responsibilities:

- login
- logout
- session user
- landing route by role

### HR Service

- [hr.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/hr.service.ts)

Current responsibilities:

- list HR users
- create HR user

### Employee Service

- [employee.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/employee.service.ts)

Current responsibilities:

- list employees
- get employee detail
- create employee
- update employee

### Attendance Service

- [attendance.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/attendance.service.ts)

Current responsibilities:

- HR attendance logs
- employee timesheets
- today attendance state
- punch in/out
- employee summary

### Dashboard Service

- [dashboard.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/dashboard.service.ts)

Current responsibilities:

- admin dashboard
- HR dashboard

### Profile Service

- [profile.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/profile.service.ts)

Current responsibilities:

- employee profile

### Mock Backend Store

- [phase1-store.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/phase1-store.service.ts)

This is the temporary backend simulator.

It currently handles:

- seeded users
- seeded HR users
- seeded employees
- seeded attendance
- dashboard values
- login validation
- password change
- employee create and update
- HR create

---

## 10. Demo Credentials

These credentials are seeded in the mock store:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@aivan.com` | `Admin@123` |
| HR | `hr@aivan.com` | `Hr@12345` |
| Employee | `kaushal@aivan.com` | `Employee@123` |
| Employee | `ananya.employee@aivan.com` | `Employee@123` |
| Employee | `rahul@aivan.com` | `Employee@123` |

---

## 11. What The Frontend Still Needs From Backend

The screen flow is ready, but the frontend still needs real backend APIs.

These are the actual service replacements needed later:

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

## 12. How To Connect Backend Later

When backend is ready, follow this order:

1. update `AuthService`
2. update `HrService`
3. update `EmployeeService`
4. update `AttendanceService`
5. update `DashboardService`
6. update `MyProfileService`

### Important Rule

Do not replace every service in one go.

Replace one service, test one screen flow, then move to next service.

That is the safest approach.

---

## 13. Step By Step Frontend-to-Backend Integration Plan

### Step 1. Auth

Replace:

- store-based login

With:

- `HttpClient.post('/api/v1/auth/login')`

Then store token and user session.

### Step 2. HR Module

Replace:

- HR list mock
- create HR mock

With backend calls.

### Step 3. Employee Module

Replace:

- employee list
- employee detail
- create employee
- update employee

### Step 4. Attendance Module

Replace:

- attendance list
- employee punch flow
- employee timesheets
- employee summary

### Step 5. Dashboard Module

Replace:

- admin dashboard
- HR dashboard

### Step 6. Profile And Password

Replace:

- employee profile
- change password

---

## 14. Validation Already Present In Frontend

Some validation is already implemented on the frontend:

- login email format
- required login password
- add employee required fields
- mobile number pattern
- temporary password min length
- date of birth past date validation
- create HR email and phone validation

Backend must still validate everything again.

Frontend validation is helpful, but backend validation is mandatory.

---

## 15. Current Phase 1 Completion Status

### Completed In Frontend

- login flow
- admin role flow
- HR role flow
- employee role flow
- route guards
- dashboards
- create HR screen
- HR users list
- employee list
- add employee
- employee detail/edit
- attendance pages
- employee profile
- change password
- seeded mock data

### Still Pending In Frontend

- real API integration
- JWT token storage flow
- backend error handling polish
- production backend environment wiring

---

## 16. Final Recommendation

Frontend Phase 1 is already in a strong shape.

The correct next step is **not** rebuilding screens.

The correct next step is:

1. keep this frontend structure
2. build backend to match these models and services
3. replace store calls with real API calls step by step

This is the cleanest and safest Phase 1 path.

