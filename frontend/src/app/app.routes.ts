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
import { LoginActivityList } from './features/login-activity/login-activity-list';
import { LoginActivityDetail } from './features/login-activity/login-activity-detail';
import { LoginActivityRedirect } from './features/login-activity/login-activity-redirect';
import { RegularizationComponent } from './features/emp/pages/regularization/regularization';
import { RegularizationRequestsComponent } from './features/hr/pages/regularization-requests/regularization-requests';
import { EmpTimeOffComponent } from './features/emp/pages/time-off/time-off';

import { MasterDataComponent } from './features/master/pages/master-data/master-data';
import { ManagersComponent } from './features/hr/pages/managers/managers';
import { ManagerDashboard } from './features/manager/pages/manager-dashboard/manager-dashboard';
import { ManagerHomeComponent } from './features/manager/pages/manager-home/manager-home';
import { ManagerTeamComponent } from './features/manager/pages/manager-team/manager-team';
import { ManagerAttendanceComponent } from './features/manager/pages/manager-attendance/manager-attendance';
import { ManagerTimeOffComponent } from './features/manager/pages/manager-time-off/manager-time-off';

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
      { path: 'managers', component: ManagersComponent },
      { path: 'time-off', component: HrTimeOffComponent },
      { path: 'my-profile', component: MyProfile },
      { path: 'login-activity', component: LoginActivityList },
      { path: 'login-activity/:id', component: LoginActivityDetail },
      { path: 'regularization-requests', component: RegularizationRequestsComponent },
      { path: 'payroll', loadComponent: () => import('./features/hr/pages/payroll/payroll').then(m => m.PayrollComponent) },
      { path: 'payroll/:tab', loadComponent: () => import('./features/hr/pages/payroll/payroll').then(m => m.PayrollComponent) },
      { path: 'documents', loadComponent: () => import('./features/hr/pages/hr-documents/hr-documents').then(m => m.HrDocumentsComponent) },
      { path: 'reports', loadComponent: () => import('./features/hr/pages/reports/reports').then(m => m.HRReportsComponent) },
      { path: 'trainings', loadComponent: () => import('./features/hr/pages/trainings/training-list/training-list').then(m => m.TrainingListComponent) },
      { path: 'trainings/create', loadComponent: () => import('./features/hr/pages/trainings/training-form/training-form').then(m => m.TrainingFormComponent) },
      { path: 'trainings/:id/edit', loadComponent: () => import('./features/hr/pages/trainings/training-form/training-form').then(m => m.TrainingFormComponent) },
      { path: 'trainings/:id/manage', loadComponent: () => import('./features/hr/pages/trainings/training-manage/training-manage').then(m => m.TrainingManageComponent) },
      { path: 'trainings/:id/view', loadComponent: () => import('./features/emp/pages/training-view/training-view').then(m => m.TrainingViewComponent) },
      { path: 'trainings/:id/assessment', loadComponent: () => import('./features/hr/pages/trainings/assessment-builder/assessment-builder').then(m => m.AssessmentBuilderComponent) },
      { path: 'training-reports', loadComponent: () => import('./features/hr/pages/trainings/training-reports/training-reports').then(m => m.TrainingReportsComponent) },
    ]
  },
  { 
    path: 'emp-dashboard', 
    component: EmpDashboard,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin', 'hr', 'employee', 'manager'] },
    children: [
      { path: 'my-attendance', component: MyAttendance },
      { path: 'my-documents', loadComponent: () => import('./features/emp/pages/my-documents/my-documents').then(m => m.MyDocumentsComponent) },
      { path: 'regularization', component: RegularizationComponent },
      { path: 'my-profile', component: MyProfile },
      { path: 'change-password', component: ChangePasswordComponent },
      { path: 'time-off', component: EmpTimeOffComponent },
      { path: 'my-payroll', loadComponent: () => import('./features/emp/pages/my-payroll/my-payroll').then(m => m.MyPayrollComponent) },
      { path: 'my-trainings', loadComponent: () => import('./features/emp/pages/my-trainings/my-trainings').then(m => m.MyTrainingsComponent) },
      { path: 'my-trainings/:id', loadComponent: () => import('./features/emp/pages/training-view/training-view').then(m => m.TrainingViewComponent) },
      { path: 'trainings/:id/view', loadComponent: () => import('./features/emp/pages/training-view/training-view').then(m => m.TrainingViewComponent) },
      { path: 'assessment/:id', loadComponent: () => import('./features/emp/pages/assessment-exam/assessment-exam').then(m => m.AssessmentExamComponent) },
      { path: 'assessment-result/:id', loadComponent: () => import('./features/emp/pages/assessment-result/assessment-result').then(m => m.AssessmentResultComponent) },
      { path: 'manager-dashboard', component: ManagerHomeComponent },
      { path: 'team', component: ManagerTeamComponent },
      { path: 'team-attendance', component: ManagerAttendanceComponent },
      { path: 'leave-approvals', component: ManagerTimeOffComponent },
      // HR Management child routes inside emp-dashboard (opens on same page)
      { path: 'hr-overview', component: HrDashboard },
      { path: 'hr-employees', component: Employees },
      { path: 'hr-managers', component: ManagersComponent },
      { path: 'hr-documents', loadComponent: () => import('./features/hr/pages/hr-documents/hr-documents').then(m => m.HrDocumentsComponent) },
      { path: 'hr-attendance', component: AttendanceComponent },
      { path: 'hr-time-off', component: HrTimeOffComponent },
      { path: 'hr-regularization', component: RegularizationRequestsComponent },
      { path: 'hr-trainings', loadComponent: () => import('./features/hr/pages/trainings/training-list/training-list').then(m => m.TrainingListComponent) },
      { path: 'trainings', loadComponent: () => import('./features/hr/pages/trainings/training-list/training-list').then(m => m.TrainingListComponent) },
      { path: 'trainings/create', loadComponent: () => import('./features/hr/pages/trainings/training-form/training-form').then(m => m.TrainingFormComponent) },
      { path: 'trainings/:id/edit', loadComponent: () => import('./features/hr/pages/trainings/training-form/training-form').then(m => m.TrainingFormComponent) },
      { path: 'trainings/:id/manage', loadComponent: () => import('./features/hr/pages/trainings/training-manage/training-manage').then(m => m.TrainingManageComponent) },
      { path: 'trainings/:id/assessment', loadComponent: () => import('./features/hr/pages/trainings/assessment-builder/assessment-builder').then(m => m.AssessmentBuilderComponent) },
      { path: 'training-reports', loadComponent: () => import('./features/hr/pages/trainings/training-reports/training-reports').then(m => m.TrainingReportsComponent) },
      { path: 'hr-reports', loadComponent: () => import('./features/hr/pages/reports/reports').then(m => m.HRReportsComponent) },
      { path: 'hr-payroll', loadComponent: () => import('./features/hr/pages/payroll/payroll').then(m => m.PayrollComponent) },
      { path: 'hr-payroll/:tab', loadComponent: () => import('./features/hr/pages/payroll/payroll').then(m => m.PayrollComponent) },
    ]
  },
  {
    path: 'manager-dashboard',
    component: ManagerDashboard,
    canActivate: [authGuard, roleGuard],
    data: { roles: ['admin', 'manager', 'employee'] },
    children: [
      { path: '', component: ManagerHomeComponent },
      { path: 'team', component: ManagerTeamComponent },
      { path: 'attendance', component: ManagerAttendanceComponent },
      { path: 'time-off', component: ManagerTimeOffComponent },
      { path: 'my-profile', component: MyProfile }
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
      { path: 'managers', component: ManagersComponent },
      { path: 'documents', loadComponent: () => import('./features/hr/pages/hr-documents/hr-documents').then(m => m.HrDocumentsComponent) },
      { path: 'attendance', component: AttendanceComponent },
      { path: 'time-off', component: HrTimeOffComponent },
      { path: 'my-profile', component: MyProfile },
      { path: 'login-activity', component: LoginActivityList },
      { path: 'login-activity/:id', component: LoginActivityDetail },
      { path: 'regularization-requests', component: RegularizationRequestsComponent },
      { path: 'payroll', loadComponent: () => import('./features/hr/pages/payroll/payroll').then(m => m.PayrollComponent) },
      { path: 'payroll/:tab', loadComponent: () => import('./features/hr/pages/payroll/payroll').then(m => m.PayrollComponent) },
      { path: 'reports', loadComponent: () => import('./features/master/pages/reports/reports').then(m => m.AdminReportsComponent) },
      { path: 'master-data', component: MasterDataComponent },
      { path: 'trainings', loadComponent: () => import('./features/hr/pages/trainings/training-list/training-list').then(m => m.TrainingListComponent) },
      { path: 'trainings/create', loadComponent: () => import('./features/hr/pages/trainings/training-form/training-form').then(m => m.TrainingFormComponent) },
      { path: 'trainings/:id/edit', loadComponent: () => import('./features/hr/pages/trainings/training-form/training-form').then(m => m.TrainingFormComponent) },
      { path: 'trainings/:id/manage', loadComponent: () => import('./features/hr/pages/trainings/training-manage/training-manage').then(m => m.TrainingManageComponent) },
      { path: 'trainings/:id/view', loadComponent: () => import('./features/emp/pages/training-view/training-view').then(m => m.TrainingViewComponent) },
      { path: 'trainings/:id/assessment', loadComponent: () => import('./features/hr/pages/trainings/assessment-builder/assessment-builder').then(m => m.AssessmentBuilderComponent) },
      { path: 'training-reports', loadComponent: () => import('./features/hr/pages/trainings/training-reports/training-reports').then(m => m.TrainingReportsComponent) },
    ]
  },
  { path: 'login-activity', component: LoginActivityRedirect, canActivate: [authGuard] },
  { path: 'notifications/login-activity/:id', component: LoginActivityRedirect, canActivate: [authGuard] },
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' },
];
