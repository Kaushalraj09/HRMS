# Phase 1 Backend Implementation Guide

## 1. What This Document Is For

This document is the **backend implementation guide for Phase 1** of the Aivan HRMS Portal.

It is written for a fresher developer who is handling **both frontend and backend**.

This version is now aligned with the **actual frontend already implemented**.

Phase 1 frontend already has:

- login page
- admin dashboard
- admin HR list
- admin create HR page
- admin employee list
- HR dashboard
- HR employee list
- HR add employee
- HR employee detail/edit
- HR attendance page
- employee dashboard
- employee attendance page
- employee profile page
- employee change password page

The frontend currently works on a browser-based mock store. Your backend job is to replace that mock store with **real APIs and real database data**.

This document explains:

- what to build first
- in what order to build it
- what folder structure to use
- what database tables to create
- what exact APIs the frontend needs
- how to connect backend to the frontend later

---

## 2. Phase 1 Scope

### Must Be Implemented

- single login for `admin`, `hr`, and `employee`
- admin can create HR users
- admin can view HR users
- admin can view employees
- HR can create employee with login access in same flow
- HR can view employee list
- HR can view employee detail
- HR can edit employee detail
- HR can view attendance history
- employee can login and view own dashboard
- employee can view own attendance
- employee can punch in and punch out
- employee can view own profile
- employee can change password
- admin and HR dashboards should return real values from database

### Not Required In Phase 1

- payroll
- leave approval workflow
- project/client management
- document upload
- notifications
- multi-company tenancy
- mobile app APIs

---

## 3. First Important Rule

Do **not** start by building every table and every API.

For Phase 1, the safest order is:

1. project setup
2. database connection
3. auth
4. admin create HR
5. employee create/edit/list/detail
6. attendance
7. dashboards
8. profile and password change
9. connect frontend APIs one by one

If you try to build everything together, it will become confusing very fast.

---

## 4. How To Think About The System

There are 3 user roles in the same portal:

- `admin`
- `hr`
- `employee`

### Access Flow

1. Admin logs in
2. Admin lands on master dashboard
3. Admin creates HR account
4. HR logs in
5. HR lands on HR dashboard
6. HR creates employee account with login
7. Employee logs in
8. Employee lands on employee dashboard

### Phase 1 Role Responsibility

#### Admin

- create HR
- view HR list
- view employee list
- view admin dashboard

#### HR

- create employee
- view employee list
- edit employee
- view attendance history
- view HR dashboard

#### Employee

- login
- view own dashboard
- punch in/out
- view own attendance
- view own profile
- change password

---

## 5. Recommended Backend Stack

Use:

- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- Uvicorn
- Passlib or pwdlib for password hashing
- python-jose or PyJWT for JWT tokens

This is good because:

- FastAPI is simple and beginner-friendly
- SQLAlchemy is standard and works well with PostgreSQL
- Alembic helps you manage schema changes safely
- JWT works well for single portal role-based auth

---

## 6. Backend Folder Structure

Create this structure:

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   └── constants.py
│   ├── api/
│   │   └── v1/
│   │       ├── auth_routes.py
│   │       ├── hr_routes.py
│   │       ├── employee_routes.py
│   │       ├── attendance_routes.py
│   │       ├── dashboard_routes.py
│   │       └── profile_routes.py
│   ├── models/
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── hr_user.py
│   │   ├── employee.py
│   │   ├── attendance.py
│   │   └── master_data.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── hr.py
│   │   ├── employee.py
│   │   ├── attendance.py
│   │   ├── dashboard.py
│   │   └── profile.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── hr_service.py
│   │   ├── employee_service.py
│   │   ├── attendance_service.py
│   │   ├── dashboard_service.py
│   │   └── profile_service.py
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── hr_repository.py
│   │   ├── employee_repository.py
│   │   └── attendance_repository.py
│   └── seeds/
│       ├── seed_master_data.py
│       └── seed_demo_users.py
├── alembic/
├── requirements.txt
└── .env
```

### What Each Folder Means

#### `core/`

This is for project-level logic:

- environment variables
- database session
- password hashing
- JWT helpers
- role helper functions

#### `api/v1/`

This is where API routes live.

Each file should only define route handlers.

#### `models/`

This is where SQLAlchemy database models live.

#### `schemas/`

This is where Pydantic request and response models live.

#### `services/`

This is where business logic goes.

Example:

- create employee + create login + validate email uniqueness

That logic should live in `employee_service.py`, not directly inside route handler.

#### `repositories/`

This is optional but good practice.

This is where raw DB query logic goes.

If you are fresher and want to keep it simple, you can begin with route -> service -> model, and add repository layer later.

---

## 7. Where To Start Step By Step

This is the most important section.

Follow this exact order.

### Step 1. Create The Backend App Skeleton

Inside `backend/`:

1. create virtual environment
2. install FastAPI, SQLAlchemy, Alembic, PostgreSQL driver
3. create `app/main.py`
4. create `core/config.py`
5. create `core/database.py`
6. create base route `/health`

### Step 2. Setup Database Connection

In `core/database.py`:

- create SQLAlchemy engine
- create session maker
- create declarative base

Do not create business logic yet.

First confirm:

- app starts
- DB connects
- `/health` works

### Step 3. Create The Main User Table

Create `users` table first.

Without this, nothing else can login.

### Step 4. Build Login API First

Frontend login is already ready.

So first real API should be:

- `POST /api/v1/auth/login`

Once login works, route guards and role redirects become real.

### Step 5. Build Admin HR APIs

After login:

- create HR
- list HR users

This supports admin area.

### Step 6. Build Employee APIs

After HR APIs:

- create employee with login
- list employee
- get employee detail
- update employee

This supports admin and HR employee screens.

### Step 7. Build Attendance APIs

After employee APIs:

- HR attendance history
- employee timesheets
- employee today attendance state
- employee punch API
- employee summary

### Step 8. Build Dashboard APIs

After attendance APIs:

- admin dashboard
- HR dashboard

### Step 9. Build Profile And Change Password APIs

After dashboards:

- employee profile
- change password

### Step 10. Connect Frontend One Service At A Time

Do not switch all frontend services at once.

Replace them one by one:

1. auth service
2. HR service
3. employee service
4. attendance service
5. dashboard service
6. profile service

---

## 8. Beginner-Friendly Setup Commands

Example setup:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg[binary] pydantic-settings python-jose passlib[bcrypt]
```

Create `requirements.txt` after install:

```bash
pip freeze > requirements.txt
```

Create `.env`:

```env
APP_NAME=Aivan HRMS Portal API
APP_ENV=development
APP_PORT=8000
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aivan_hrms
JWT_SECRET_KEY=change-this-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Start backend:

```bash
uvicorn app.main:app --reload --port 8000
```

---

## 9. Database Design For Phase 1

Keep Phase 1 simple.

Do not over-normalize too early.

For Phase 1, these are enough:

### 9.1 Core Tables

- `roles`
- `users`
- `hr_users`
- `employees`
- `attendance_records`

### 9.2 Lookup Tables

- `departments`
- `designations`
- `employment_types`
- `work_locations`
- `shift_types`

You can keep lookup tables simple in Phase 1.

---

## 10. Exact Database Schema

Use PostgreSQL.

### 10.1 Roles Table

```sql
CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL
);
```

Seed values:

- `admin`
- `hr`
- `employee`

### 10.2 Users Table

This is the login table.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id BIGINT NOT NULL REFERENCES roles(id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    linked_hr_id UUID NULL,
    linked_employee_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 10.3 HR Users Table

```sql
CREATE TABLE hr_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hr_code VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    login VARCHAR(20) NOT NULL DEFAULT 'Enabled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 10.4 Employees Table

```sql
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    employee_code VARCHAR(30) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(100) NOT NULL,
    employee_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    login VARCHAR(20) NOT NULL DEFAULT 'Enabled',
    official_email VARCHAR(255) NOT NULL UNIQUE,
    personal_email VARCHAR(255) NULL,
    mobile VARCHAR(20) NOT NULL,
    alternate_mobile VARCHAR(20) NULL,
    emergency_contact_name VARCHAR(150) NULL,
    emergency_contact_number VARCHAR(20) NULL,
    gender VARCHAR(20) NULL,
    dob DATE NULL,
    marital_status VARCHAR(30) NULL,
    blood_group VARCHAR(10) NULL,
    work_location VARCHAR(150) NULL,
    shift_type VARCHAR(100) NULL,
    doj DATE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 10.5 Attendance Records Table

For Phase 1, one daily record per employee per day is enough.

```sql
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL,
    check_in TIME NULL,
    check_out TIME NULL,
    break_minutes INTEGER NOT NULL DEFAULT 0,
    overtime_minutes INTEGER NOT NULL DEFAULT 0,
    work_mode VARCHAR(20) NOT NULL DEFAULT 'Office',
    status VARCHAR(30) NOT NULL DEFAULT 'Not Marked',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (employee_id, attendance_date)
);
```

### 10.6 Lookup Tables

```sql
CREATE TABLE departments (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE designations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE employment_types (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE work_locations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE shift_types (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);
```

---

## 11. Seed Data You Must Add

You need demo data so frontend and backend can be tested quickly.

### Roles

- admin
- hr
- employee

### Departments

- Engineering
- Human Resources
- Finance
- Marketing
- Sales
- Support

### Designations

- Frontend Developer
- Backend Developer
- HR Executive
- HR Manager
- Finance Analyst

### Employment Types

- Full-Time
- Contract
- Intern

### Work Locations

- Indore Office
- Remote Home Office
- Hybrid

### Shift Types

- General Shift
- Night Shift

### Demo Users

- `admin@aivan.com` / `Admin@123`
- `hr@aivan.com` / `Hr@12345`
- `kaushal@aivan.com` / `Employee@123`
- `ananya.employee@aivan.com` / `Employee@123`
- `rahul@aivan.com` / `Employee@123`

Important:

- store only hashed passwords in DB
- keep same demo credentials for development seed

---

## 12. Backend Models You Need

Create SQLAlchemy models for:

- `Role`
- `User`
- `HrUser`
- `Employee`
- `AttendanceRecord`

### Relationship Rule

- one `User` belongs to one role
- one HR login should link to one `HrUser`
- one employee login should link to one `Employee`

This is enough for Phase 1.

---

## 13. Exact APIs The Frontend Needs

This section is the most important for integration.

These APIs must match the current frontend models.

---

## 14. Auth APIs

### 14.1 POST `/api/v1/auth/login`

Used by:

- login page

Frontend file:

- [auth.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/auth.service.ts)

### Request

```json
{
  "email": "admin@aivan.com",
  "password": "Admin@123"
}
```

### Response

```json
{
  "accessToken": "jwt-access-token",
  "refreshToken": "jwt-refresh-token",
  "tokenType": "bearer",
  "expiresIn": 3600,
  "me": {
    "id": "uuid",
    "email": "admin@aivan.com",
    "displayName": "Master Admin",
    "role": "admin",
    "linkedEmployeeId": null,
    "linkedHrId": null,
    "status": "Active"
  }
}
```

### Notes

- verify password hash
- create JWT token
- return same response shape as frontend model

### 14.2 GET `/api/v1/auth/me`

Used for:

- future refresh
- route-based user bootstrap

### Response

Same `me` object as login response.

### 14.3 POST `/api/v1/auth/change-password`

Used by:

- employee change password page

### Request

```json
{
  "currentPassword": "Employee@123",
  "newPassword": "Employee@456",
  "confirmPassword": "Employee@456"
}
```

### Response

```json
{
  "success": true,
  "message": "Password updated successfully"
}
```

---

## 15. Admin HR APIs

### 15.1 GET `/api/v1/hr-users`

Used by:

- admin HR users list page

### Query Params

- `page`
- `limit`
- `search`
- `status`

Example:

```text
/api/v1/hr-users?page=1&limit=8&search=ananya&status=Active
```

### Response

```json
{
  "data": [
    {
      "id": "uuid",
      "userId": "uuid",
      "hrCode": "HR-001",
      "fullName": "Ananya Sharma",
      "email": "hr@aivan.com",
      "phone": "9876500100",
      "department": "Human Resources",
      "designation": "HR Manager",
      "status": "Active",
      "login": "Enabled",
      "createdAt": "2026-01-10"
    }
  ],
  "total": 1
}
```

### 15.2 POST `/api/v1/hr-users`

Used by:

- admin create HR page

### Request

```json
{
  "fullName": "New HR User",
  "email": "newhr@aivan.com",
  "phone": "9876500101",
  "designation": "HR Executive",
  "department": "Human Resources",
  "temporaryPassword": "Hr@12345",
  "status": "Active"
}
```

### Response

```json
{
  "success": true,
  "message": "New HR User created successfully as HR",
  "hr": {
    "id": "uuid",
    "userId": "uuid",
    "hrCode": "HR-002",
    "fullName": "New HR User",
    "email": "newhr@aivan.com",
    "phone": "9876500101",
    "department": "Human Resources",
    "designation": "HR Executive",
    "status": "Active",
    "login": "Enabled",
    "createdAt": "2026-04-14"
  }
}
```

### Backend Logic

When this API is called:

1. validate email uniqueness
2. hash temporary password
3. create `hr_users` row
4. create `users` row with role `hr`
5. link user to hr row
6. return created HR object

---

## 16. Employee APIs

### 16.1 GET `/api/v1/employees`

Used by:

- HR employee list
- admin employee list

### Query Params

- `page`
- `limit`
- `search`
- `department`
- `type`
- `status`

Example:

```text
/api/v1/employees?page=1&limit=10&search=kaushal&department=Engineering&type=Full-Time&status=Active
```

### Response

```json
{
  "data": [
    {
      "id": "uuid",
      "userId": "uuid",
      "employeeCode": "EMP-001",
      "name": "Kaushal Raj",
      "firstName": "Kaushal",
      "lastName": "Raj",
      "department": "Engineering",
      "designation": "Frontend Developer",
      "employeeType": "Full-Time",
      "status": "Active",
      "login": "Enabled",
      "officialEmail": "kaushal@aivan.com",
      "personalEmail": "kaushal.personal@gmail.com",
      "mobile": "9876543210",
      "alternateMobile": "9876500001",
      "emergencyContactName": "Rakesh Raj",
      "emergencyContactNumber": "9876500002",
      "gender": "Male",
      "dob": "1998-03-22",
      "maritalStatus": "Single",
      "bloodGroup": "B+",
      "workLocation": "Indore Office",
      "shiftType": "General Shift",
      "doj": "2025-10-01"
    }
  ],
  "total": 1
}
```

### 16.2 GET `/api/v1/employees/{employee_id}`

Used by:

- employee detail page

### Response

```json
{
  "employee": {
    "id": "uuid",
    "userId": "uuid",
    "employeeCode": "EMP-001",
    "name": "Kaushal Raj",
    "firstName": "Kaushal",
    "lastName": "Raj",
    "department": "Engineering",
    "designation": "Frontend Developer",
    "employeeType": "Full-Time",
    "status": "Active",
    "login": "Enabled",
    "officialEmail": "kaushal@aivan.com",
    "personalEmail": "kaushal.personal@gmail.com",
    "mobile": "9876543210",
    "alternateMobile": "9876500001",
    "emergencyContactName": "Rakesh Raj",
    "emergencyContactNumber": "9876500002",
    "gender": "Male",
    "dob": "1998-03-22",
    "maritalStatus": "Single",
    "bloodGroup": "B+",
    "workLocation": "Indore Office",
    "shiftType": "General Shift",
    "doj": "2025-10-01"
  },
  "managerName": "Assigned HR Team",
  "loginEmail": "kaushal@aivan.com",
  "temporaryPasswordHint": "Temp password set during account creation"
}
```

### 16.3 POST `/api/v1/employees`

Used by:

- add employee page

### Request

This must match the current frontend payload exactly:

```json
{
  "accountAccess": {
    "loginEmail": "new.employee@aivan.com",
    "temporaryPassword": "Employee@123",
    "role": "employee"
  },
  "personalInfo": {
    "firstName": "New",
    "lastName": "Employee",
    "gender": "Male",
    "dob": "1998-01-10",
    "maritalStatus": "Single",
    "bloodGroup": "B+"
  },
  "employmentInfo": {
    "employeeType": "Full-Time",
    "department": "Engineering",
    "designation": "Frontend Developer",
    "workLocation": "Indore Office",
    "shiftType": "General Shift",
    "doj": "2026-04-14"
  },
  "contactInfo": {
    "officialEmail": "new.employee@aivan.com",
    "personalEmail": "new.employee@gmail.com",
    "mobile": "9876500200",
    "alternateMobile": "9876500201",
    "emergencyContactName": "Father Name",
    "emergencyContactNumber": "9876500202"
  }
}
```

### Response

```json
{
  "success": true,
  "message": "New Employee created successfully. Login email: new.employee@aivan.com",
  "employee": {
    "id": "uuid",
    "userId": "uuid",
    "employeeCode": "EMP-004",
    "name": "New Employee",
    "firstName": "New",
    "lastName": "Employee",
    "department": "Engineering",
    "designation": "Frontend Developer",
    "employeeType": "Full-Time",
    "status": "Active",
    "login": "Enabled",
    "officialEmail": "new.employee@aivan.com",
    "personalEmail": "new.employee@gmail.com",
    "mobile": "9876500200",
    "alternateMobile": "9876500201",
    "emergencyContactName": "Father Name",
    "emergencyContactNumber": "9876500202",
    "gender": "Male",
    "dob": "1998-01-10",
    "maritalStatus": "Single",
    "bloodGroup": "B+",
    "workLocation": "Indore Office",
    "shiftType": "General Shift",
    "doj": "2026-04-14"
  }
}
```

### Backend Logic

This should happen in one transaction:

1. validate official email uniqueness
2. validate login email uniqueness
3. generate next employee code if not sent
4. hash temporary password
5. create user row with role `employee`
6. create employee row
7. update user.linked_employee_id
8. create today blank attendance row optionally
9. commit transaction

### 16.4 PUT `/api/v1/employees/{employee_id}`

Used by:

- employee detail edit page

### Request

Use the same structure as employee create payload.

### Response

```json
{
  "success": true,
  "message": "Employee updated successfully"
}
```

---

## 17. Attendance APIs

### 17.1 GET `/api/v1/attendance`

Used by:

- HR attendance page

### Query Params

- `page`
- `limit`
- `fromDate`
- `toDate`
- `search`
- `department`
- `status`

### Response

```json
{
  "data": [
    {
      "id": "uuid",
      "code": "EMP-001",
      "name": "Kaushal Raj",
      "department": "Engineering",
      "date": "2026-04-14",
      "checkIn": "09:05",
      "checkOut": "18:15",
      "hours": "8h 25m",
      "status": "Present"
    }
  ],
  "total": 1,
  "metrics": {
    "present": 1,
    "checkedIn": 0,
    "notMarked": 0,
    "checkedOut": 0
  }
}
```

### 17.2 GET `/api/v1/attendance/me/timesheets`

Used by:

- employee attendance page
- employee dashboard table

### Response

```json
[
  {
    "date": "2026-04-14",
    "day": "Mon",
    "entry": "09:05",
    "exit": "18:15",
    "total": "8h 25m",
    "overtime": "0h 15m",
    "break": "0h 45m",
    "grandTotal": "8h 40m",
    "status": "Present"
  }
]
```

### 17.3 GET `/api/v1/attendance/me/today`

Used by:

- employee dashboard

### Response

```json
{
  "isPunchedIn": false,
  "status": "Not Marked",
  "approvedHours": 2,
  "remainingHours": 8,
  "workMode": "Office"
}
```

### 17.4 POST `/api/v1/attendance/me/punch`

Used by:

- employee dashboard punch button

### Request

```json
{
  "workMode": "Office"
}
```

### Response

Same shape as `GET /attendance/me/today`.

### Backend Logic

If no record for today:

- create one
- set `check_in`
- set status `Checked In`

If record exists with `check_in` but no `check_out`:

- set `check_out`
- calculate break/overtime if needed
- set status `Checked Out`

### 17.5 GET `/api/v1/attendance/me/summary`

Used by:

- employee dashboard attendance summary

### Response

```json
[
  {
    "label": "Total Days",
    "value": 7,
    "icon": "fas fa-calendar total blue-icon"
  },
  {
    "label": "Worked Days",
    "value": 6,
    "icon": "fas fa-calendar-check worked blue-icon"
  }
]
```

---

## 18. Dashboard APIs

### 18.1 GET `/api/v1/dashboard/admin`

Used by:

- admin dashboard

### Response

Must match frontend admin dashboard model:

```json
{
  "cards": [
    {
      "icon": "fas fa-user-shield",
      "label": "Total HR Users",
      "value": "1"
    }
  ],
  "hrUsers": [
    {
      "primary": "Ananya Sharma",
      "secondary": "hr@aivan.com",
      "tertiary": "Human Resources · HR Manager",
      "status": "Active"
    }
  ],
  "employees": [
    {
      "primary": "Kaushal Raj",
      "secondary": "kaushal@aivan.com",
      "tertiary": "Engineering · Frontend Developer",
      "status": "Active"
    }
  ]
}
```

### 18.2 GET `/api/v1/dashboard/hr`

Used by:

- HR dashboard

### Response

```json
{
  "totalEmployees": 3,
  "presentEmployees": 2,
  "checkedInEmployees": 1,
  "checkedOutEmployees": 0,
  "notMarkedEmployees": 0,
  "workModeBreakdown": [1, 2],
  "genderBreakdown": [1, 2],
  "quickStats": [
    { "total": 1, "name": "HR Users" },
    { "total": 3, "name": "Departments" }
  ],
  "recentTimeSheets": [
    {
      "employee": "Kaushal Raj",
      "date": "2026-04-14",
      "punchIn": "09:05",
      "punchOut": "18:15",
      "breakTime": "45 mins",
      "overtime": "15 mins",
      "totalHours": "8h 25m",
      "status": "Present"
    }
  ]
}
```

---

## 19. Profile API

### 19.1 GET `/api/v1/profile/me`

Used by:

- employee profile page

### Response

```json
{
  "id": "uuid",
  "employeeId": "EMP-001",
  "firstName": "Kaushal",
  "lastName": "Raj",
  "initials": "KR",
  "role": "Frontend Developer",
  "department": "Engineering",
  "shift": "General Shift",
  "status": "Active",
  "personalDetails": {
    "firstName": "Kaushal",
    "lastName": "Raj",
    "gender": "Male",
    "dateOfBirth": "1998-03-22",
    "maritalStatus": "Single",
    "bloodGroup": "B+"
  },
  "contactDetails": {
    "officialEmail": "kaushal@aivan.com",
    "personalEmail": "kaushal.personal@gmail.com",
    "mobileNumber": "9876543210",
    "alternateMobile": "9876500001",
    "location": "Indore Office"
  }
}
```

---

## 20. Route And Service Mapping

This is how frontend services should map to backend APIs later.

### AuthService

Current frontend file:

- [auth.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/auth.service.ts)

Replace local store calls with:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

### HrService

Current frontend file:

- [hr.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/hr.service.ts)

Replace with:

- `GET /api/v1/hr-users`
- `POST /api/v1/hr-users`

### EmployeeService

Current frontend file:

- [employee.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/employee.service.ts)

Replace with:

- `GET /api/v1/employees`
- `GET /api/v1/employees/{id}`
- `POST /api/v1/employees`
- `PUT /api/v1/employees/{id}`

### AttendanceService

Current frontend file:

- [attendance.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/attendance.service.ts)

Replace with:

- `GET /api/v1/attendance`
- `GET /api/v1/attendance/me/timesheets`
- `GET /api/v1/attendance/me/today`
- `POST /api/v1/attendance/me/punch`
- `GET /api/v1/attendance/me/summary`

### DashboardService

Current frontend file:

- [dashboard.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/dashboard.service.ts)

Replace with:

- `GET /api/v1/dashboard/admin`
- `GET /api/v1/dashboard/hr`

### ProfileService

Replace with:

- `GET /api/v1/profile/me`

---

## 21. Step By Step Implementation Plan For Kaushal

This is the exact recommended order.

### Day 1. Backend Setup

Do only this:

1. create FastAPI project
2. create DB connection
3. create `.env`
4. run app
5. make `/health` API

Do not build business modules yet.

### Day 2. User, Role, Auth

Do this:

1. create `roles` table
2. create `users` table
3. seed admin, hr, employee roles
4. seed demo accounts
5. create `POST /auth/login`
6. create JWT token helper
7. create dependency to get current user

After this, test login from Postman first.

### Day 3. HR Module

Do this:

1. create `hr_users` table
2. create `GET /hr-users`
3. create `POST /hr-users`
4. test admin can create HR

### Day 4. Employee Module

Do this:

1. create `employees` table
2. create `GET /employees`
3. create `GET /employees/{id}`
4. create `POST /employees`
5. create `PUT /employees/{id}`

Important:

`POST /employees` must create both:

- login user
- employee record

in one transaction.

### Day 5. Attendance Module

Do this:

1. create `attendance_records` table
2. create HR attendance API
3. create employee timesheet API
4. create employee today attendance API
5. create punch API
6. create summary API

### Day 6. Dashboard Module

Do this:

1. create admin dashboard API
2. create HR dashboard API
3. build aggregate queries

### Day 7. Profile And Password

Do this:

1. create profile API
2. create change password API
3. verify all employee self-service pages

### Day 8. Frontend Integration

Do this one service at a time:

1. replace auth mock with backend call
2. replace HR service mock
3. replace employee service mock
4. replace attendance service mock
5. replace dashboard service mock
6. replace profile service mock

Do not replace all services together.

---

## 22. How To Write One API Properly

Use this method for every API.

Example: `POST /api/v1/hr-users`

### Step A. Schema

Create request schema and response schema in `schemas/hr.py`.

### Step B. Model

Make sure DB model exists in `models/hr_user.py`.

### Step C. Service

Write business logic in `services/hr_service.py`.

### Step D. Route

Add endpoint in `api/v1/hr_routes.py`.

### Step E. Test

Test in Postman or curl.

### Step F. Connect Frontend

After API works, replace frontend mock method with real HTTP call.

Use the same pattern for every module.

---

## 23. Basic Security Rules

Even in Phase 1, do not skip these:

- never store plain passwords
- always hash passwords
- protect APIs with JWT auth
- restrict routes by role
- employee should only access own profile and own attendance
- admin-only APIs must check admin role
- HR-only write APIs must check admin or HR role

### Simple Role Protection Example

- admin routes: only `admin`
- HR routes: `admin`, `hr`
- employee self routes: only `employee`

---

## 24. Validation Rules

### Create HR

- email must be unique
- phone should be valid format
- password min length 8

### Create Employee

- official email must be unique
- login email must be unique
- mobile must be valid
- first name required
- last name required
- DOB valid date
- joining date valid date

### Punch API

- employee must exist
- one attendance row per employee per date
- do not create duplicate record for same date

---

## 25. Testing Checklist

Before connecting frontend, backend developer should test:

### Auth

- valid login
- invalid login
- inactive user login blocked

### HR

- create HR success
- duplicate HR email fails
- HR list pagination works

### Employee

- create employee success
- duplicate official email fails
- duplicate login email fails
- employee detail returns data
- employee update works

### Attendance

- HR attendance filter works
- employee timesheet works
- employee today status works
- punch in works
- punch out works

### Dashboard

- admin dashboard values load
- HR dashboard values load

### Profile

- employee profile loads
- change password works

---

## 26. Biggest Mistakes To Avoid

### Mistake 1

Creating frontend payloads different from the current frontend models.

Fix:

Follow the payloads in this document exactly.

### Mistake 2

Writing all DB logic directly inside route files.

Fix:

Keep routes thin, use services.

### Mistake 3

Creating employee record without login user.

Fix:

Create both in one transaction.

### Mistake 4

Trying to build payroll or leave module now.

Fix:

Stay inside Phase 1 scope.

### Mistake 5

Replacing all frontend services at once.

Fix:

Replace one service at a time and test after each.

---

## 27. Final Recommendation

If Kaushal is starting from zero, this is the cleanest path:

1. make backend run
2. make login work
3. make admin create HR work
4. make HR create employee work
5. make attendance work
6. make dashboard work
7. connect frontend gradually

That is the correct Phase 1 implementation path.

Do not optimize too early.
Do not over-abstract too early.
Do not try to make Phase 2 features now.

First make the existing frontend screens run on real APIs.

---

## 28. Frontend Files Waiting For Backend

These frontend files are the main integration points:

- [auth.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/auth.service.ts)
- [hr.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/hr.service.ts)
- [employee.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/employee.service.ts)
- [attendance.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/attendance.service.ts)
- [dashboard.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/dashboard.service.ts)
- [profile.service.ts](/Users/vivekmehta/Development/Vivek/AIVan/Aivan-HRMS-Portal/frontend/src/app/core/services/profile.service.ts)

When backend APIs are ready, these services should stop using local store and start using `HttpClient`.

---

## 29. Done Means

Phase 1 backend is complete when:

- login works for admin, HR, employee
- admin can create HR
- admin can view HR list
- admin can view employee list
- HR can create employee with login
- HR can view and edit employee
- HR can view attendance history
- employee can punch in/out
- employee can view own attendance
- employee can view own profile
- employee can change password
- admin dashboard returns real data
- HR dashboard returns real data
- frontend services are connected to backend instead of local mock store

