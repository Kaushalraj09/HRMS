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
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { RegularizationService } from '../../../../core/services/regularization.service';


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

  pendingRegularizations: any[] = [];
  selectedRegularization: any = null;
  activeCategoryTab: 'timeoff' | 'regularization' = 'timeoff';

  reasonTypeOptions: any[] = [
    { label: 'Missed Punch', value: 'missed_punch' },
    { label: 'Forgot Punch In', value: 'forgot_punch_in' },
    { label: 'Forgot Punch Out', value: 'forgot_punch_out' },
    { label: 'Late Arrival Sync', value: 'late_sync' },
    { label: 'System/Network Issue', value: 'system_issue' },
    { label: 'Other', value: 'other' }
  ];

  private sub = new Subscription();

  constructor(
    private sidebarService: MasterSidebarService,
    private router: Router,
    private readonly dashboardService: DashboardService,
    private readonly authService: AuthService,
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly regularizationService: RegularizationService,
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
    this.loadPendingRegularizations();

    // WebSocket updates
    this.sub.add(
      this.timeoffService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
        this.loadPendingRegularizations();
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
    this.timeoffService.getPendingTimeOffRequests(1, 100).subscribe(res => {
      this.pendingRequests = res.items || [];
      this.cdr.detectChanges();
    });
  }

  loadProcessedRequests() {
    this.timeoffService.getProcessedTimeOffRequests(1, 100).subscribe(res => {
      this.processedRequests = res.items || [];
      this.cdr.detectChanges();
    });
  }

  processRequest(requestId: number, action: string) {
    let approvedHours: number | undefined;
    if (action === 'APPROVE') {
      const req = this.pendingRequests.find(r => r.id === requestId);
      approvedHours = req?.duration_hours;
    }
    
    this.timeoffService.approveTimeOffRequest(requestId, action, approvedHours).subscribe({
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

  loadPendingRegularizations() {
    this.regularizationService.getPendingRequests(1, 100).subscribe(res => {
      this.pendingRegularizations = res.items || [];
      this.cdr.detectChanges();
    });
  }

  processRegularization(requestId: number, status: 'approved' | 'rejected') {
    this.regularizationService.submitDecision(requestId, { status, reviewComment: 'Admin Oversight Decision' }).subscribe({
      next: () => {
        alert(`Regularization request ${status} successfully`);
        this.loadPendingRegularizations();
      },
      error: (err) => alert(err?.error?.detail || "Error processing regularization request")
    });
  }

  viewRegularizationDetails(req: any): void {
    this.selectedRegularization = req;
  }

  closeRegularizationModal(): void {
    this.selectedRegularization = null;
  }

  processRegularizationFromModal(requestId: number, status: 'approved' | 'rejected'): void {
    this.processRegularization(requestId, status);
    this.closeRegularizationModal();
  }

  getReasonTypeLabel(type: string): string {
    const option = this.reasonTypeOptions.find(opt => opt.value === type);
    return option ? option.label : type;
  }

  formatTime(timeStr?: string | null): string {
    if (!timeStr) return '-';
    const parts = timeStr.split(':');
    if (parts.length >= 2) {
      return `${parts[0]}:${parts[1]}`;
    }
    return timeStr;
  }
}
