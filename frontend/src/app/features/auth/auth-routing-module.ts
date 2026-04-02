import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login.component';
import { HrDashboard } from '../hr-dashboard/hr-dashboard';
import { EmpDashboard } from '../emp-dashboard/emp-dashboard';
import { MasterDashboard } from '../master-dashboard/master-dashboard';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'hr-dashboard', component: HrDashboard },
  { path: 'emp-dashboard', component: EmpDashboard },
  { path: 'master-dashboard', component: MasterDashboard }

];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AuthRoutingModule { }
