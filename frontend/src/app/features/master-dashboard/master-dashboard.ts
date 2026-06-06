import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../shared/shared-module';
import { Sidebar } from '../../shared/components/sidebar/sidebar';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
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
  dashboardError = '';
  isMainRoute = false;

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
    this.updateMainRouteState();

    // Subscribe to router events to update route state dynamically
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.updateMainRouteState();
      this.cdr.detectChanges();
    });

    // Subscribe to current user details dynamically
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.userName = user.displayName || 'System Admin';
        this.cdr.detectChanges();
      }
    });

    this.dashboardService.getAdminDashboard().subscribe({
      next: (data) => {
        this.dashboardError = '';
        this.dashboardData = data;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.dashboardError = error?.error?.detail || 'Unable to load master dashboard data.';
        this.cdr.detectChanges();
      }
    });
  }

  toggleSidebar() {
    this.sidebarService.toggleSidebar();
  }

  private updateMainRouteState() {
    const cleanUrl = this.router.url.split('?')[0].split('#')[0].replace(/\/$/, '');
    this.isMainRoute = cleanUrl === '/master-dashboard' || cleanUrl === '/master-dashboard/main';
  }

  isMainDashboardRoute(): boolean {
    return this.isMainRoute;
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
