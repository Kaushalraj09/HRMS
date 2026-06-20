import { Routes } from '@angular/router';
import { Login } from './features/auth/pages/login/login';
import { ForgotPassword } from './features/auth/pages/forgot-password/forgot-password';
import { ResetPassword } from './features/auth/pages/reset-password/reset-password';
import { HrDashboard } from './features/hr/pages/hr-dashboard/hr-dashboard';
import { EmpDashboard } from './features/emp/pages/emp-dashboard/emp-dashboard';
import { MasterDashboard } from './features/master/pages/master-dashboard/master-dashboard';
import { MyAttendance } from './features/emp/pages/my-attendance/my-attendance';
import { MyProfile } from './features/emp/pages/my-profile/my-profile';
import { ChangePasswordComponent } from './features/emp/pages/change-password/change-password';

import { AttendanceComponent } from './features/hr/pages/attendance/attendance';
import { Employees } from './features/hr/pages/employees/employees';
import { HrTimeOffComponent } from './features/hr/pages/time-off/time-off';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { HrUsersComponent } from './features/master/pages/hr-users/hr-users';
import { AdminEmployeesComponent } from './features/master/pages/admin-employees/admin-employees';
import { LoginActivityList } from './features/login-activity/login-activity-list';
import { LoginActivityDetail } from './features/login-activity/login-activity-detail';
import { LoginActivityRedirect } from './features/login-activity/login-activity-redirect';
import { RegularizationComponent } from './features/emp/pages/regularization/regularization';
import { RegularizationRequestsComponent } from './features/hr/pages/regularization-requests/regularization-requests';

export const routes: Routes = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  {
    path: 'auth',
    children: [
      { path: 'login', component: Login },
      { path: 'forgot-password', component: ForgotPassword },
      { path: 'reset-password', component: ResetPassword }
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
      { path: 'time-off', component: HrTimeOffComponent },
      { path: 'my-profile', component: MyProfile },
      { path: 'login-activity', component: LoginActivityList },
      { path: 'login-activity/:id', component: LoginActivityDetail },
      { path: 'regularization-requests', component: RegularizationRequestsComponent },
      { path: 'reports', loadComponent: () => import('./features/hr/pages/reports/reports').then(m => m.HRReportsComponent) }
    ]
  },
  { 
    path: 'emp-dashboard', 
    component: EmpDashboard,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin', 'employee'] },
    children: [
      { path: 'my-attendance', component: MyAttendance },
      { path: 'regularization', component: RegularizationComponent },
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
      { path: 'employees', component: Employees },
      { path: 'attendance', component: AttendanceComponent },
      { path: 'time-off', component: HrTimeOffComponent },
      { path: 'my-profile', component: MyProfile },
      { path: 'login-activity', component: LoginActivityList },
      { path: 'login-activity/:id', component: LoginActivityDetail },
      { path: 'regularization-requests', component: RegularizationRequestsComponent },
      { path: 'reports', loadComponent: () => import('./features/master/pages/reports/reports').then(m => m.AdminReportsComponent) }
    ]
  },
  { path: 'login-activity', component: LoginActivityRedirect, canActivate: [authGuard] },
  { path: 'notifications/login-activity/:id', component: LoginActivityRedirect, canActivate: [authGuard] },
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' },
];
