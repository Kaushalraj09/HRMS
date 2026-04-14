import { Routes } from '@angular/router';
import { Login } from './features/auth/pages/login/login';
import { ForgotPassword } from './features/auth/pages/forgot-password/forgot-password';
import { HrDashboard } from './features/hr/pages/hr-dashboard/hr-dashboard';
import { EmpDashboard } from './features/emp/pages/emp-dashboard/emp-dashboard';
import { MasterDashboard } from './features/master-dashboard/master-dashboard';
import { MyAttendance } from './features/emp/pages/my-attendance/my-attendance';
import { MyProfile } from './features/emp/pages/my-profile/my-profile';
import { ChangePasswordComponent } from './features/emp/pages/change-password/change-password';
import { AttendanceComponent } from './features/hr/pages/attendance/attendance';
import { Employees } from './features/hr/pages/employees/employees';
import { AddEmployeeComponent } from './features/hr/pages/employees/add-employee/add-employee';
import { EmployeeDetailComponent } from './features/hr/pages/employees/employee-detail/employee-detail';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { HrUsersComponent } from './features/admin/pages/hr-users/hr-users';
import { AddHrComponent } from './features/admin/pages/add-hr/add-hr';
import { AdminEmployeesComponent } from './features/admin/pages/admin-employees/admin-employees';

export const routes: Routes = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  {
    path: 'auth',
    children: [
      { path: 'login', component: Login },
      { path: 'forgot-password', component: ForgotPassword }
    ],
  },
  { 
    path: 'hr-dashboard', 
    component: HrDashboard,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin', 'hr'] },
    children: [
      { path: 'attendance', component: AttendanceComponent },
      { path: 'employees', component: Employees },
      { path: 'employees/add', component: AddEmployeeComponent },
      { path: 'employees/:employeeId', component: EmployeeDetailComponent }
    ]
  },
  { 
    path: 'emp-dashboard', 
    component: EmpDashboard,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin', 'employee'] },
    children: [
      { path: 'my-attendance', component: MyAttendance },
      { path: 'my-profile', component: MyProfile },
      { path: 'change-password', component: ChangePasswordComponent }
    ]
  },
  {
    path: 'master-dashboard',
    component: MasterDashboard,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin'] },
    children: [
      { path: 'hr-users', component: HrUsersComponent },
      { path: 'hr-users/add', component: AddHrComponent },
      { path: 'employees', component: AdminEmployeesComponent }
    ]
  },
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' },
];
