import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login.component';
import { HrDashboardComponent } from '../hr-dashboard/hrDashboard.component';

const routes: Routes = [
  {path: 'login', component: LoginComponent},
  {path: 'hr-dashboard', component: HrDashboardComponent}
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AuthRoutingModule {}
