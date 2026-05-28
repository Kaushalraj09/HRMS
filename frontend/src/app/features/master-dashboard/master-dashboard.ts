import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../shared/shared-module';
import { Sidebar } from '../../shared/components/sidebar/sidebar';
import { RouterModule, Router } from '@angular/router';
import { SidebarService } from '../../shared/components/sidebar/sidebar.service';

import { DashboardService } from '../../core/services/dashboard.service';
import { AdminDashboardData } from '../../core/models/dashboard.model';
import { AuthService } from '../../core/services/auth.service';


@Component({
  selector: 'app-master-dashboard',
  imports: [MatFormFieldModule, MatSelectModule, CommonModule, FormsModule, SharedModule, Sidebar, RouterModule],
  standalone: true,
  templateUrl: './master-dashboard.html',
  styleUrl: './master-dashboard.css',
})
export class MasterDashboard implements OnInit {
  selectedLang = 'en';
  isSidebarOpen$!: import('rxjs').Observable<boolean>;
  dashboardData: AdminDashboardData | null = null;
  userName = 'Admin';

  constructor(
    private sidebarService: SidebarService,
    private router: Router,
    private readonly dashboardService: DashboardService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isSidebarOpen$ = this.sidebarService.isSidebarOpen$;
    this.userName = this.authService.getDisplayName();
  }

  ngOnInit() {
    this.dashboardService.getAdminDashboard().subscribe(data => {
      this.dashboardData = data;
      this.cdr.detectChanges();
    });
  }

  toggleSidebar() {
    this.sidebarService.toggleSidebar();
  }

  isMainDashboardRoute(): boolean {
    return this.router.url === '/master-dashboard' || this.router.url === '/master-dashboard/main';
  }
  onSearch(event: any) {
    console.log('Search:', event);
  }
  openProfile() {
    console.log('Opening profile');
  }
  openNotifications() {
    console.log('Opening notifications');
  }

  get fullDetails() {
    return this.dashboardData?.cards || [];
  }

  get hrUsers() {
    return this.dashboardData?.hrUsers || [];
  }

  get employees() {
    return this.dashboardData?.employees || [];
  }
}
