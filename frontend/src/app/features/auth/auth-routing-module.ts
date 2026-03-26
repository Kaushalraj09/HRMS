import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login.component';
import { HrDashboardComponent } from '../hr-dashboard/hrDashboard.component';
import { EmpDashboardComponent } from '../emp-dashboard/empdashboard.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'hr-dashboard', component: HrDashboardComponent },
  { path: 'emp-dashboard', component: EmpDashboardComponent }

];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AuthRoutingModule { }
