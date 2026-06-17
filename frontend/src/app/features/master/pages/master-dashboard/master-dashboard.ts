import { Component, OnInit, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Navbar } from '../../../../shared/components/navbar/navbar';
import { MasterSidebar } from '../../components/master-sidebar/master-sidebar';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { MasterSidebarService } from '../../components/master-sidebar/master-sidebar.service';
import { Subscription } from 'rxjs';

import { DashboardService } from '../../../../core/services/dashboard.service';
import { AdminDashboardData } from '../../../../core/models/dashboard.model';
import { AuthService } from '../../../../core/services/auth.service';
import { AttendanceService } from '../../../../core/services/attendance.service';


@Component({
  selector: 'app-master-dashboard',
  imports: [MatFormFieldModule, MatSelectModule, CommonModule, FormsModule, Navbar, MasterSidebar, RouterModule],
  standalone: true,
  templateUrl: './master-dashboard.html',
  styleUrl: './master-dashboard.css',
})
export class MasterDashboard implements OnInit, OnDestroy {
  selectedLang = 'en';
  isSidebarOpen$!: import('rxjs').Observable<boolean>;
  dashboardData: AdminDashboardData | null = null;
  userName = 'Admin';
  dashboardError = '';
  isMainRoute = false;
  searchTerm = '';
  pendingRequests: any[] = [];
  processedRequests: any[] = [];
  selectedRequest: any = null;
  activeOversightTab = 'pending';
  private sub = new Subscription();

  constructor(
    private sidebarService: MasterSidebarService,
    private router: Router,
    private readonly dashboardService: DashboardService,
    private readonly authService: AuthService,
    private readonly attendanceService: AttendanceService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isSidebarOpen$ = this.sidebarService.isSidebarOpen$;
    this.userName = this.authService.getDisplayName();
  }

  ngOnInit() {
    this.updateMainRouteState();

    // Subscribe to router events to update route state dynamically
    this.sub.add(
      this.router.events.pipe(
        filter(event => event instanceof NavigationEnd)
      ).subscribe(() => {
        this.updateMainRouteState();
        this.cdr.detectChanges();
      })
    );

    // Subscribe to current user details dynamically
    this.sub.add(
      this.authService.currentUser$.subscribe(user => {
        if (user) {
          this.userName = user.displayName || 'System Admin';
          this.cdr.detectChanges();
        }
      })
    );

    this.sub.add(
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
      })
    );

    this.loadPendingRequests();
    this.loadProcessedRequests();

    // WebSocket updates
    this.sub.add(
      this.attendanceService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
      })
    );
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
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
  onSearch(term: string) {
    this.searchTerm = term || '';
  }
  openProfile() {
    console.log('Opening profile');
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

  get filteredHrUsers() {
    return this.hrUsers.filter((row) => this.matchesSearch([row.primary, row.secondary, row.tertiary, row.status]));
  }

  get filteredEmployees() {
    return this.employees.filter((row) => this.matchesSearch([row.primary, row.secondary, row.tertiary, row.status]));
  }

  private matchesSearch(values: Array<string | number | undefined | null>): boolean {
    const query = this.searchTerm.trim().toLowerCase();
    if (!query) {
      return true;
    }

    return values.some((value) => String(value ?? '').toLowerCase().includes(query));
  }

  loadPendingRequests() {
    this.attendanceService.getPendingTimeOffRequests().subscribe(requests => {
      this.pendingRequests = requests;
      this.cdr.detectChanges();
    });
  }

  loadProcessedRequests() {
    this.attendanceService.getProcessedTimeOffRequests().subscribe(requests => {
      this.processedRequests = requests;
      this.cdr.detectChanges();
    });
  }

  processRequest(requestId: number, action: string) {
    let approvedHours: number | undefined;
    if (action === 'APPROVE') {
      const req = this.pendingRequests.find(r => r.id === requestId);
      approvedHours = req?.duration_hours;
    }
    
    this.attendanceService.approveTimeOffRequest(requestId, action, approvedHours).subscribe({
      next: () => {
        alert(`Request ${action.toLowerCase()}d successfully`);
        this.loadPendingRequests();
        this.loadProcessedRequests();
      },
      error: (err) => alert(err?.error?.detail || "Error processing request")
    });
  }

  viewRequestDetails(req: any): void {
    this.selectedRequest = req;
  }

  closeDetailsModal(): void {
    this.selectedRequest = null;
  }

  processRequestFromModal(requestId: number, action: string): void {
    this.processRequest(requestId, action);
    this.closeDetailsModal();
  }

  downloadAttachment(fileName: string): void {
    alert(`Downloading attachment: ${fileName}`);
  }

  setOversightTab(tab: string) {
    this.activeOversightTab = tab;
    this.cdr.detectChanges();
  }
}
