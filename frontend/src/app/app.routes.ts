import { Routes } from '@angular/router';
import { Login } from './features/auth/pages/login/login';
import { HrDashboard } from './features/hr-dashboard/hr-dashboard';
import { EmpDashboard } from './features/emp-dashboard/emp-dashboard';
import { MasterDashboard } from './features/master-dashboard/master-dashboard';

export const routes: Routes = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  {
    path: 'auth',
    children: [{ path: 'login', component: Login }],
  },
  { path: 'hr-dashboard', component: HrDashboard },
  { path: 'emp-dashboard', component: EmpDashboard },
  { path: 'master-dashboard', component: MasterDashboard},
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: '**', redirectTo: 'auth/login' },
];
