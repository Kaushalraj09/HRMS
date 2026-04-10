# Phase 1 Frontend Implementation Specification

## 1. Objective

This document defines the exact Angular implementation plan for Phase 1:

- shared login portal for `admin`, `hr`, and `employee`
- HR dashboard
- HR attendance history
- add employee wizard with account creation
- employee dashboard with today, weekly, monthly attendance and profile summary

The existing frontend already includes:

- auth pages
- HR dashboard page
- employee dashboard page
- master dashboard page
- shared navbar/sidebar components

Phase 1 implementation must extend these assets instead of discarding them.

---

## 2. Current Files to Reuse and Modify

### Reuse / Modify

- [frontend/src/app/app.routes.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/app.routes.ts)
- [frontend/src/app/services/auth.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/services/auth.ts)
- [frontend/src/app/features/auth/pages/login/login.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/auth/pages/login/login.ts)
- [frontend/src/app/features/auth/pages/login/login.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/auth/pages/login/login.html)
- [frontend/src/app/features/hr-dashboard/hr-dashboard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr-dashboard/hr-dashboard.ts)
- [frontend/src/app/features/hr-dashboard/hr-dashboard.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr-dashboard/hr-dashboard.html)
- [frontend/src/app/features/emp-dashboard/emp-dashboard.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp-dashboard/emp-dashboard.ts)
- [frontend/src/app/features/emp-dashboard/emp-dashboard.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp-dashboard/emp-dashboard.html)

### Fix Before Starting

- remove merge conflict markers from [frontend/src/app/features/emp-dashboard/emp-dashboard.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp-dashboard/emp-dashboard.html)

---

## 3. Target Angular Folder Map

```text
frontend/
└── src/
    └── app/
        ├── app.config.ts                           (modify)
        ├── app.routes.ts                           (modify)
        ├── core/
        │   ├── constants/
        │   │   ├── api-endpoints.ts
        │   │   └── storage-keys.ts
        │   ├── guards/
        │   │   ├── auth.guard.ts
        │   │   └── role.guard.ts
        │   ├── interceptors/
        │   │   └── auth.interceptor.ts
        │   └── utils/
        │       ├── role-redirect.ts
        │       └── date-range.util.ts
        ├── models/
        │   ├── auth.models.ts
        │   ├── employee.models.ts
        │   ├── attendance.models.ts
        │   ├── dashboard.models.ts
        │   └── master-data.models.ts
        ├── services/
        │   ├── auth.ts                             (modify)
        │   ├── employee.service.ts
        │   ├── attendance.service.ts
        │   ├── dashboard.service.ts
        │   └── master-data.service.ts
        ├── features/
        │   ├── auth/
        │   │   ├── auth-module.ts                  (existing)
        │   │   ├── auth-routing-module.ts          (existing)
        │   │   └── pages/
        │   │       ├── login/                      (modify)
        │   │       ├── forgot-password/            (existing)
        │   │       └── first-login/
        │   │           ├── first-login.ts
        │   │           ├── first-login.html
        │   │           └── first-login.css
        │   ├── hr-dashboard/                       (modify existing)
        │   ├── hr-attendance/
        │   │   ├── pages/
        │   │   │   └── attendance-history/
        │   │   │       ├── attendance-history.ts
        │   │   │       ├── attendance-history.html
        │   │   │       └── attendance-history.css
        │   │   └── components/
        │   │       ├── attendance-filter-bar/
        │   │       └── attendance-summary-cards/
        │   ├── hr-employees/
        │   │   ├── pages/
        │   │   │   ├── employee-list/
        │   │   │   │   ├── employee-list.ts
        │   │   │   │   ├── employee-list.html
        │   │   │   │   └── employee-list.css
        │   │   │   ├── add-employee/
        │   │   │   │   ├── add-employee.ts
        │   │   │   │   ├── add-employee.html
        │   │   │   │   └── add-employee.css
        │   │   │   └── employee-detail/
        │   │   │       ├── employee-detail.ts
        │   │   │       ├── employee-detail.html
        │   │   │       └── employee-detail.css
        │   │   └── components/
        │   │       ├── employee-personal-form/
        │   │       ├── employee-account-form/
        │   │       ├── employee-job-form/
        │   │       ├── employee-attendance-form/
        │   │       └── employee-review-panel/
        │   ├── emp-dashboard/                      (modify existing)
        │   └── emp-profile/
        │       └── pages/
        │           └── profile/
        │               ├── profile.ts
        │               ├── profile.html
        │               └── profile.css
        └── shared/
            ├── shared-module.ts                    (modify as needed)
            └── components/                         (reuse existing navbar/sidebar)
```

---

## 4. Route Design

### Final Route Table

| Path | Component | Roles |
|---|---|---|
| `/auth/login` | Login | public |
| `/auth/forgot-password` | Forgot Password | public |
| `/auth/first-login` | First Login | employee/admin/hr |
| `/hr/dashboard` | HrDashboard | admin, hr |
| `/hr/attendance` | AttendanceHistory | admin, hr |
| `/hr/employees` | EmployeeList | admin, hr |
| `/hr/employees/new` | AddEmployee | admin, hr |
| `/hr/employees/:employeeId` | EmployeeDetail | admin, hr |
| `/employee/dashboard` | EmpDashboard | employee |
| `/employee/profile` | Profile | employee |

### Route Guard Rules

- `auth.guard.ts`
  - redirects unauthenticated users to `/auth/login`
- `role.guard.ts`
  - checks route `data.roles`
  - redirects to default landing route if role mismatch

### Role Redirect Logic

- `admin` -> `/hr/dashboard`
- `hr` -> `/hr/dashboard`
- `employee` -> `/employee/dashboard`

---

## 5. Frontend Data Models

### auth.models.ts

```ts
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoggedInUser {
  id: string;
  employeeId: string | null;
  fullName: string;
  email: string;
  roles: string[];
  primaryRole: 'admin' | 'hr' | 'employee';
  firstLoginRequired: boolean;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
  me: LoggedInUser;
}
```

### master-data.models.ts

```ts
export interface DepartmentOption {
  id: number;
  code: string;
  name: string;
}

export interface DesignationOption {
  id: number;
  code: string;
  name: string;
  departmentId: number | null;
}

export interface ShiftTemplateOption {
  id: number;
  code: string;
  name: string;
  startTime: string;
  endTime: string;
}
```

### employee.models.ts

```ts
export interface CreateEmployeeRequest {
  account: {
    officialEmail: string;
    loginEmail: string;
    roleCode: 'employee';
    passwordSetupMode: 'setup_link' | 'temporary_password';
    temporaryPassword?: string | null;
  };
  personal: {
    firstName: string;
    lastName: string;
    phone: string;
    dateOfBirth?: string | null;
    genderCode?: string | null;
    personalEmail?: string | null;
    emergencyContactName?: string | null;
    emergencyContactPhone?: string | null;
  };
  job: {
    employeeCode: string;
    departmentId: number;
    designationId: number;
    employmentTypeId: number;
    workModeId: number;
    officeLocationId: number;
    shiftTemplateId: number;
    holidayCalendarId: number;
    weekendPolicyId: number;
    managerEmployeeId?: string | null;
    joiningDate: string;
  };
  attendanceProfile: {
    allowWebPunch: boolean;
    graceMinutesOverride?: number | null;
    timezone: string;
  };
}

export interface CreateEmployeeResponse {
  employeeId: string;
  userId: string;
  employeeCode: string;
  accountStatus: string;
  firstLoginRequired: boolean;
  passwordSetupMode: 'setup_link' | 'temporary_password';
}
```

### attendance.models.ts

```ts
export interface PunchRequest {
  direction: 'in' | 'out';
  source: 'web';
  workModeCode: 'office' | 'remote' | 'hybrid';
  officeLocationId?: number | null;
  remarks?: string | null;
}

export interface TodayAttendanceResponse {
  attendanceDate: string;
  firstIn: string | null;
  lastOut: string | null;
  statusCode: string;
  totalWorkMinutes: number;
  totalBreakMinutes: number;
  overtimeMinutes: number;
  latestDirection: 'in' | 'out' | null;
}
```

---

## 6. Frontend Services

### auth.ts

Must expose:

- `login(payload: LoginRequest)`
- `getMe()`
- `setSession(response: LoginResponse)`
- `clearSession()`
- `getAccessToken()`
- `getCurrentUser()`
- `isLoggedIn()`

### master-data.service.ts

Must expose:

- `getBootstrap()`
- `getDepartments()`
- `getDesignations()`
- `getShifts()`
- `getLocations()`
- `getManagers()`

### employee.service.ts

Must expose:

- `createEmployee(payload: CreateEmployeeRequest)`
- `getEmployees(params)`
- `getEmployeeById(employeeId)`
- `updateEmployee(employeeId, payload)`

### attendance.service.ts

Must expose:

- `punch(payload: PunchRequest)`
- `getMyTodayAttendance()`
- `getMyWeeklyAttendance(params)`
- `getMyMonthlyAttendance(params)`
- `getMyAttendanceHistory(params)`
- `getHrAttendanceHistory(params)`
- `getHrAttendanceSummary(params)`

### dashboard.service.ts

Must expose:

- `getHrDashboardSummary(params)`
- `getEmployeeDashboardSummary()`

---

## 7. Screen Specifications

## 7.1 Login Page

### Existing Base

- [login.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/auth/pages/login/login.html)

### Required Behavior

- submit `email` and `password`
- show loader during API call
- on success:
  - save token
  - save current user
  - redirect by role
- on failure:
  - show inline toast/banner error

### Validation

- email required
- valid email format
- password required
- min length 6

## 7.2 HR Dashboard

### Existing Base

- [hr-dashboard.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/hr-dashboard/hr-dashboard.html)

### Required API Data

- total employees
- present employees
- absent employees
- late employees
- work mode breakdown
- gender breakdown
- recent attendance rows
- upcoming birthdays/events

### Widget API Mapping

| Widget | API |
|---|---|
| KPI cards | `GET /api/v1/attendance/hr/summary` |
| recent time sheets | `GET /api/v1/attendance/hr/history?limit=10` |
| work mode breakdown | `GET /api/v1/attendance/hr/summary` |
| gender breakdown | `GET /api/v1/employees?summary=true` |

## 7.3 HR Attendance History

### Filters

- date from
- date to
- employee
- department
- status
- work mode
- pagination

### Table Columns

- employee code
- employee name
- department
- date
- first in
- last out
- total hours
- overtime
- status
- work mode

## 7.4 Add Employee Wizard

### Steps

1. Account Access
2. Personal Details
3. Job Details
4. Attendance Setup
5. Review and Submit

### Step 1: Account Access Fields

- official email
- login email
- role code fixed as `employee`
- password setup mode
- temporary password if selected

### Step 2: Personal Details Fields

- first name
- last name
- phone
- personal email
- gender
- date of birth
- emergency contact name
- emergency contact phone

### Step 3: Job Details Fields

- employee code
- joining date
- department
- designation
- employment type
- work mode
- office location
- shift template
- holiday calendar
- weekend policy
- manager

### Step 4: Attendance Setup Fields

- allow web punch
- timezone
- grace minutes override optional

### Step 5: Review and Submit

- render all values read-only
- allow edit jump-back
- confirm before submit

### Validation Rules

- official email required and unique
- login email required and unique
- phone required
- employee code required and unique
- department required
- designation required
- joining date required
- work mode required
- location required
- shift required

### Submission UX

- disable submit button while request pending
- show success with employee code and login status
- show backend validation errors at field level if available

## 7.5 Employee Dashboard

### Existing Base

- [emp-dashboard.html](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/features/emp-dashboard/emp-dashboard.html)

### Required Sections

- welcome card
- today punch card
- request time off placeholder
- monthly calendar view
- schedule timeline
- timesheet table
- attendance summary
- latest news

### API Data Binding

| Section | API |
|---|---|
| today punch state | `GET /api/v1/attendance/me/today` |
| punch button | `POST /api/v1/attendance/punch` |
| week/month totals | `GET /api/v1/attendance/me/weekly`, `GET /api/v1/attendance/me/monthly` |
| timesheet table | `GET /api/v1/attendance/me/history` |
| profile snippet | `GET /api/v1/employees/{employee_id}` |

## 7.6 Employee Profile Page

### Sections

- basic profile
- contact details
- job details
- reporting manager
- shift and work mode

---

## 8. Frontend State Management

Phase 1 should stay simple:

- use service-based HTTP calls
- use Angular signals or RxJS in page-level services only where needed
- do not introduce NgRx in Phase 1

### Session State

- store JWT in local storage
- store minimal `me` object in local storage
- expose current user via signal or `BehaviorSubject`

### Filter State

- attendance history filter state can stay inside feature component
- reuse query param sync for date range and page

---

## 9. Form Strategy

### Use Angular Reactive Forms For

- login
- add employee wizard
- attendance filter bar
- first-login password setup

### Recommended Wizard Form Structure

```ts
this.form = this.fb.group({
  account: this.fb.group({
    officialEmail: ['', [Validators.required, Validators.email]],
    loginEmail: ['', [Validators.required, Validators.email]],
    passwordSetupMode: ['setup_link', Validators.required],
    temporaryPassword: ['']
  }),
  personal: this.fb.group({
    firstName: ['', Validators.required],
    lastName: ['', Validators.required],
    phone: ['', Validators.required],
    personalEmail: [''],
    genderCode: [''],
    dateOfBirth: [''],
    emergencyContactName: [''],
    emergencyContactPhone: ['']
  }),
  job: this.fb.group({
    employeeCode: ['', Validators.required],
    joiningDate: ['', Validators.required],
    departmentId: [null, Validators.required],
    designationId: [null, Validators.required],
    employmentTypeId: [null, Validators.required],
    workModeId: [null, Validators.required],
    officeLocationId: [null, Validators.required],
    shiftTemplateId: [null, Validators.required],
    holidayCalendarId: [null, Validators.required],
    weekendPolicyId: [null, Validators.required],
    managerEmployeeId: [null]
  }),
  attendanceProfile: this.fb.group({
    allowWebPunch: [true, Validators.required],
    timezone: ['Asia/Kolkata', Validators.required],
    graceMinutesOverride: [null]
  })
});
```

---

## 10. Frontend API Integration Rules

### HTTP Rules

- all secured API calls go through auth interceptor
- bearer token attached automatically
- 401 -> clear session -> redirect to login
- 403 -> redirect to correct home page with access denied toast

### Date Rules

- frontend sends ISO date strings: `YYYY-MM-DD`
- datetime values displayed in user timezone
- backend remains source of truth for attendance date calculations

---

## 11. UI Error States

### Login

- invalid credentials
- inactive account
- first login required

### Add Employee

- duplicate email
- duplicate employee code
- invalid manager reference
- invalid shift or location
- backend unavailable

### Attendance History

- no results
- invalid date range
- unauthorized access

### Employee Dashboard

- no attendance yet today
- missing punch state
- punch API failed

---

## 12. Frontend Testing Plan

### Unit Tests

- auth service token/session handling
- auth guard route blocking
- role guard redirects
- login form validation
- add employee wizard validation
- employee dashboard punch button state handling

### Component Tests

- HR dashboard renders API data
- attendance history filter changes query params
- employee wizard shows backend field errors
- employee dashboard updates after punch action

### Manual QA Checklist

- login works for admin/hr/employee
- admin/hr redirected to HR area
- employee redirected to employee area
- employee creation form loads all dropdowns
- employee created successfully
- employee first login works
- employee dashboard shows correct data
- HR attendance filters work

---

## 13. Frontend Developer Task Breakdown

### Task Group A: Foundation

1. Clean existing merge conflict in employee dashboard template.
2. Create `core/guards/auth.guard.ts`.
3. Create `core/guards/role.guard.ts`.
4. Create `core/interceptors/auth.interceptor.ts`.
5. Add interceptor registration in [app.config.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/app.config.ts).
6. Extend [auth.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/services/auth.ts) with session helpers.
7. Update [app.routes.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/app.routes.ts) for new role routes.

### Task Group B: Shared Models and Services

1. Add `models/auth.models.ts`.
2. Add `models/employee.models.ts`.
3. Add `models/attendance.models.ts`.
4. Add `models/master-data.models.ts`.
5. Add `services/master-data.service.ts`.
6. Add `services/employee.service.ts`.
7. Add `services/attendance.service.ts`.
8. Add `services/dashboard.service.ts`.

### Task Group C: Auth Flow

1. Update login page submit logic.
2. Add success redirect by role.
3. Add `first-login` page and route.
4. Implement password setup form.

### Task Group D: HR Modules

1. Bind existing HR dashboard widgets to APIs.
2. Create attendance history page.
3. Create employee list page.
4. Create add employee wizard page.
5. Create reusable employee wizard section components.
6. Create employee detail page.

### Task Group E: Employee Modules

1. Bind existing employee dashboard to APIs.
2. Implement punch in/out integration.
3. Implement attendance summary widgets.
4. Create employee profile page.

### Task Group F: QA and Hardening

1. Add unit tests for guards and services.
2. Add page-level tests for forms and API error states.
3. Run `ng test`.
4. Run `ng build`.

---

## 14. Frontend Integration Dependencies on Backend

The frontend cannot finish without these backend contracts being stable:

- login payload and role response
- master data bootstrap payload
- create employee payload and validation errors
- attendance summary payload
- punch endpoint response
- employee detail payload

These payloads are defined in [phase1 backend.md](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/phase1%20backend.md).

