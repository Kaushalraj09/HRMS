import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/pages/login/login.component';
import { HrDashboardComponent } from './features/hr-dashboard/hrDashboard.component';
import { EmpDashboardComponent } from './features/emp-dashboard/empdashboard.component';

export const routes: Routes = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  {
    path: 'auth',
    children: [{ path: 'login', component: LoginComponent }],
  },
  { path: 'hr-dashboard', component: HrDashboardComponent },
  { path: 'emp-dashboard', component: EmpDashboardComponent },
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' },
];
