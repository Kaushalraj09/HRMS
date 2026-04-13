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

export const routes: Routes = [ // Force IDE reload
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
    children: [
      { path: 'attendance', component: AttendanceComponent },
      { path: 'employees', component: Employees },
      { path: 'employees/add', component: AddEmployeeComponent }
    ]
  },
  { 
    path: 'emp-dashboard', 
    component: EmpDashboard,
    children: [
      { path: 'my-attendance', component: MyAttendance },
      { path: 'my-profile', component: MyProfile },
      { path: 'change-password', component: ChangePasswordComponent }
    ]
  },
  { path: 'master-dashboard', component: MasterDashboard},
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' },
];
