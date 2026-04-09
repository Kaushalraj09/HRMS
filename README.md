# Aivan HRMS Portal - Project Repository

![Aivan HRMS](https://img.shields.io/badge/Aivan-HRMS%20Portal-blueviolet?style=for-the-badge)

Welcome to the central project repository for the Aivan HRMS (Human Resource Management System) Portal. This document serves as the absolute source of truth for repository rules, coding styles, standard operating procedures, and developer collaboration guidelines.

## 📌 1. Project Overview & Repository Purpose

### Why this Monorepo exists
This repository is configured as a **Monorepo**, meaning both the Frontend and Backend logic live within this single Git repository, separated by root-level directories. 

**The primary reasons for this structure are:**
1. **Unified Tracking**: As the project owner, I need a single dashboard to monitor daily progress, code integrations, and overall project health without switching between multiple repositories.
2. **Simplified Collaboration**: While there is a strict separation of concerns, having both codebases in one place allows developers to easily reference API endpoints, models, and shared logic if needed, ensuring the frontend and backend are always in sync.

---

## 📁 2. Folder Structure & Strict Access Rules

At the root of this project, you will see two primary folders:

```text
Aivan-HRMS-Portal/
├── frontend/     # Angular 2X+ Application (UI/UX)
├── backend/      # Python Application (APIs, Database, Business Logic)
└── README.md     # You are here
```

> [!WARNING]
> **STRICT REPOSITORY POLICY - BOUNDARY ENFORCEMENT**
> This repository uses a strict role-based folder policy to prevent accidental overwrites and maintain a clean commit history.
> 
> * **Frontend Developers**: You **MUST ONLY** create branches, modify files, and push code that affects the `frontend/` directory. You are strictly forbidden from modifying any backend configuration or source code.
> * **Backend Developers**: You **MUST ONLY** create branches, modify files, and push code that affects the `backend/` directory. You are strictly forbidden from modifying any frontend configuration or source code.
> 
> *If a feature requires a change in both directories, communicate with your counterpart and the project owner. Do not attempt to fix the other developer's code.*

---

## 🛠️ 3. Developer Guidelines & Coding Standards

To maintain a clean, readable, scalable, and professional codebase, all developers must strictly adhere to the following company coding policies. Code that does not meet these standards may be rejected.

### 3.1 Naming Conventions

#### Frontend (Angular/TypeScript)
* **Files & Folders**: Use standard Angular CLI naming conventions (`kebab-case`). 
  * *Example Folders*: `employee-dashboard/`, `shared-components/`
  * *Example Files*: `employee-dashboard.component.ts`, `auth.service.ts`
* **Variables & Functions**: Use `camelCase`. 
  * *Example*: `let employeeDetails = {};`, `function calculateMonthlySalary() { ... }`
* **Classes & Interfaces**: Use `PascalCase`.
  * *Example*: `class EmployeeService { ... }`, `interface UserProfile { ... }`

#### Backend (Python)
* **Packages, Modules & Files**: Follow PEP 8 standards. Use `snake_case`.
  * *Example Folders/Packages*: `employee_management/`, `database_utils/`
  * *Example Files*: `employee_routes.py`, `auth_middleware.py`
* **Variables & Functions**: Use `snake_case`.
  * *Example*: `employee_details = {}`, `def calculate_monthly_salary(): ...`
* **Classes**: Use `PascalCase`.
  * *Example*: `class EmployeeService:`, `class DatabaseConnection:`

### 3.2 Code Annotations and Documentation

Documentation is not optional. It is required for maintainability.

* **Function & Class Documentation**: 
  * Every public class, major interface, and business-logic function **MUST** have clear documentation explaining its purpose, incoming parameters, and return variables.
  * **Frontend**: Use standard **JSDoc** formatting above your functions.
  * **Backend**: Use standard **Python Docstrings** (`"""Docstring here"""`) inside your functions and classes.
* **Inline Comments**: Use inline comments to explain *why* complex logic is written a certain way, or to reference ticket/bug numbers. Do not use inline comments to explain *what* the code is doing (the code itself should be readable enough to tell us that).

---

## 🔄 4. Git Workflow and Collaboration Expectations

To ensure I can track real-time progress, we operate on a continuous integration and daily-push model.

### 4.1 Daily Pushes (Mandatory)
Developers are required to push their latest task updates **day-by-day** to this repository. At the end of your working day, commit your current progress and push it to your assigned remote branch. This acts as both a backup of your work and a transparent progress tracker for the project owner.

### 4.2 Branching Strategy
Never push directly to the `main` or `master` branch.
* Create a new branch for every feature or bug fix.
* **Naming format**: `[role]/[feature-name]` or `[role]/[bug-fix-name]`
  * *Frontend Example*: `frontend/login-page-ui`
  * *Backend Example*: `backend/user-auth-api`

### 4.3 Commit Messages
Use clean, descriptive commit messages starting with a standard categorization tag. This makes the Git history readable and acts as an automated changelog.

**Allowed Tags:**
* `feat:` (New feature)
* `fix:` (Bug fix)
* `refactor:` (Code changes that neither fix a bug nor add a feature)
* `docs:` (Documentation changes)
* `style:` (Formatting, missing semi colons, etc; no code change)

**Examples:**
* ✅ `feat: add employee login module and JWT integration`
* ✅ `fix: resolve date formatting bug on the admin dashboard`
* ❌ `updated files` (Unacceptable)
* ❌ `fixed stuff` (Unacceptable)

---

### Need Help?
If you encounter blockers, need clarification on requirements, or require new third-party packages to be approved, please reach out directly to the project owner before proceeding. 

Let's build a robust, high-quality Aivan HRMS system together!