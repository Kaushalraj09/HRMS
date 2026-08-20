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
import { AdminDashboardData, DepartmentDistributionItem, MonthlyHiringItem, AttendanceOverviewPoint, RecentJoinerItem, BirthdayItem, PendingApprovalsSummary } from '../../../../core/models/dashboard.model';
import { AuthService } from '../../../../core/services/auth.service';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { RegularizationService } from '../../../../core/services/regularization.service';

export interface MasterAttendancePoint {
  label: string;
  dateStr: string;
  pct: number;
  x: number;
  y: number;
  presentCount: number;
  totalCount: number;
  status: string;
}

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
  userName = 'System Admin';
  dashboardError = '';
  isMainRoute = false;
  searchTerm = '';

  // Filter dropdown states
  attendanceFilter: 'month' | 'week' | 'today' = 'month';
  hiringFilter: 'year' | 'quarter' = 'year';

  // 1. Attendance Overview Hover State
  hoveredAttendancePoint: MasterAttendancePoint | null = null;
  hoveredAttendanceIndex: number | null = null;
  attendancePoints: MasterAttendancePoint[] = [
    { label: '01 May', dateStr: '01 May 2026', pct: 20.0, x: 20, y: 160, presentCount: 1, totalCount: 4, status: 'Holiday / Start' },
    { label: '08 May', dateStr: '08 May 2026', pct: 68.0, x: 140, y: 70, presentCount: 3, totalCount: 4, status: 'Working Day' },
    { label: '15 May', dateStr: '15 May 2026', pct: 28.0, x: 260, y: 140, presentCount: 1, totalCount: 4, status: 'Weekend / Off' },
    { label: '22 May', dateStr: '22 May 2026', pct: 72.0, x: 370, y: 60, presentCount: 3, totalCount: 4, status: 'Working Day' },
    { label: '31 May', dateStr: '31 May 2026', pct: 93.0, x: 480, y: 25, presentCount: 4, totalCount: 4, status: 'All Present' }
  ];

  // 2. Employee Distribution Donut Hover State
  hoveredDeptIndex: number | null = null;
  hoveredDeptItem: DepartmentDistributionItem | null = null;

  // 3. Monthly Hiring Bar Hover State
  hoveredHiringIndex: number | null = null;
  hoveredHiringItem: MonthlyHiringItem | null = null;

  // Approvals & Oversight
  pendingRequests: any[] = [];
  processedRequests: any[] = [];
  selectedRequest: any = null;
  activeOversightTab = 'pending';

  pendingRegularizations: any[] = [];
  selectedRegularization: any = null;
  activeCategoryTab: 'timeoff' | 'regularization' = 'timeoff';
  showOversightSection = true;
  showPayrollModal = false;

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
    this.userName = this.authService.getDisplayName() || 'System Admin';
  }

  ngOnInit() {
    this.updateMainRouteState();

    this.sub.add(
      this.router.events.pipe(
        filter(event => event instanceof NavigationEnd)
      ).subscribe(() => {
        this.updateMainRouteState();
        if (this.isMainRoute) {
          this.fetchAdminDashboard();
        }
        this.cdr.detectChanges();
      })
    );

    this.sub.add(
      this.authService.currentUser$.subscribe(user => {
        if (user) {
          this.userName = user.displayName || 'System Admin';
          this.cdr.detectChanges();
        }
      })
    );

    this.fetchAdminDashboard();
    this.loadPendingRequests();
    this.loadProcessedRequests();
    this.loadPendingRegularizations();

    // WebSocket updates
    this.sub.add(
      this.timeoffService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
        this.loadPendingRegularizations();
        this.fetchAdminDashboard();
      })
    );
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }

  fetchAdminDashboard() {
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
    this.router.navigate(['/master-dashboard/my-profile']);
  }

  // Dynamic getters
  get adminInitials(): string {
    const name = this.userName || 'System Admin';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      const first = parts[0][0] || '';
      const last = parts[parts.length - 1][0] || '';
      return (first + last).toUpperCase() || 'SA';
    }
    return (parts[0] || 'SA').slice(0, 2).toUpperCase();
  }

  get adminCode(): string {
    return this.dashboardData?.adminProfile?.code || '0001';
  }

  get adminRole(): string {
    return this.dashboardData?.adminProfile?.role || 'System Admin';
  }

  get adminDepartment(): string {
    return this.dashboardData?.adminProfile?.department || 'Administration';
  }

  get adminShift(): string {
    return this.dashboardData?.adminProfile?.shift || 'General Shift';
  }

  get adminStatus(): string {
    return this.dashboardData?.adminProfile?.status || 'Punched Out';
  }

  get totalEmployeesDisplay(): string {
    const count = this.dashboardData?.totalEmployees ?? 1248;
    return Number(count).toLocaleString('en-US');
  }

  get employeeGrowthText(): string {
    const count = this.dashboardData?.employeeGrowthCount ?? 18;
    const rate = this.dashboardData?.employeeGrowthRate ?? 1.46;
    return `${count} (${rate}%) this month`;
  }

  get attendanceRateDisplay(): string {
    const rate = this.dashboardData?.attendanceRate ?? 93;
    return `${Math.round(rate)}%`;
  }

  get attendanceGrowthText(): string {
    const rate = this.dashboardData?.attendanceGrowthRate ?? 4;
    return `${rate}% vs yesterday`;
  }

  get pendingLeavesDisplay(): number {
    return this.dashboardData?.pendingLeavesCount ?? (this.pendingRequests.length + this.pendingRegularizations.length || 17);
  }

  get payrollStatusDisplay(): string {
    return this.dashboardData?.payrollStatus || 'Completed';
  }

  get payrollPeriodDisplay(): string {
    return this.dashboardData?.payrollPeriod || 'For May 2026';
  }

  get departmentDistribution(): DepartmentDistributionItem[] {
    if (this.dashboardData?.departmentDistribution && this.dashboardData.departmentDistribution.length > 0) {
      return this.dashboardData.departmentDistribution;
    }
    return [
      { name: 'Engineering', count: 499, percentage: 40, color: '#3b82f6' },
      { name: 'Operations', count: 374, percentage: 30, color: '#8b5cf6' },
      { name: 'HR', count: 187, percentage: 15, color: '#10b981' },
      { name: 'Finance', count: 187, percentage: 15, color: '#f97316' }
    ];
  }

  get monthlyHiring(): MonthlyHiringItem[] {
    if (this.dashboardData?.monthlyHiringTrend && this.dashboardData.monthlyHiringTrend.length > 0) {
      return this.dashboardData.monthlyHiringTrend;
    }
    return [
      { month: 'Jan', count: 20 },
      { month: 'Feb', count: 14 },
      { month: 'Mar', count: 30 },
      { month: 'Apr', count: 19 },
      { month: 'May', count: 26 },
      { month: 'Jun', count: 36 },
      { month: 'Jul', count: 28 },
      { month: 'Aug', count: 40 },
      { month: 'Sep', count: 27 },
      { month: 'Oct', count: 33 },
      { month: 'Nov', count: 28 },
      { month: 'Dec', count: 58 }
    ];
  }

  get recentJoiners(): RecentJoinerItem[] {
    if (this.dashboardData?.recentJoiners && this.dashboardData.recentJoiners.length > 0) {
      return this.dashboardData.recentJoiners;
    }
    return [
      { id: 1, name: 'Amit Sharma', designation: 'Software Engineer', department: 'Engineering', doj: '01 Jun 2026', initials: 'AS' },
      { id: 2, name: 'Neha Reddy', designation: 'HR Executive', department: 'Human Resources', doj: '31 May 2026', initials: 'NR' },
      { id: 3, name: 'Pawan Kumar', designation: 'Finance Associate', department: 'Finance', doj: '30 May 2026', initials: 'PK' },
      { id: 4, name: 'Sara Mistry', designation: 'UI/UX Designer', department: 'Engineering', doj: '29 May 2026', initials: 'SM' }
    ];
  }

  get todayBirthdays(): BirthdayItem[] {
    if (this.dashboardData?.todayBirthdays && this.dashboardData.todayBirthdays.length > 0) {
      return this.dashboardData.todayBirthdays;
    }
    return [
      { id: 1, name: 'Rohit Verma', designation: 'Software Developer', department: 'Engineering', dob: '17 Aug', initials: 'RV', isToday: true },
      { id: 2, name: 'Anjali Mehta', designation: 'HR Generalist', department: 'Human Resources', dob: '19 Aug', initials: 'AM', isToday: false },
      { id: 3, name: 'Vikram Singh', designation: 'Operations Executive', department: 'Operations', dob: '22 Aug', initials: 'VS', isToday: false }
    ];
  }

  get pendingApprovalsSummary(): PendingApprovalsSummary {
    return this.dashboardData?.pendingApprovals || {
      leaveRequests: this.pendingRequests.length || 8,
      timeOffRequests: 3,
      regularizationRequests: this.pendingRegularizations.length || 1,
      expenseClaims: 2
    };
  }

  // SVG Chart helpers
  getDonutOffset(index: number): number {
    const dist = this.departmentDistribution;
    let accumulatedPercent = 0;
    for (let i = 0; i < index; i++) {
      accumulatedPercent += dist[i].percentage;
    }
    // Circumference = 2 * PI * 40 = 251.327
    const circumference = 251.327;
    return -((accumulatedPercent / 100) * circumference);
  }

  getDonutDashArray(percentage: number): string {
    const circumference = 251.327;
    const filled = (percentage / 100) * circumference;
    return `${filled} ${circumference - filled}`;
  }

  getHiringBarHeight(count: number): number {
    const maxVal = 60;
    return Math.min(100, Math.max(10, (count / maxVal) * 100));
  }

  // Attendance Hover Handlers
  setAttendanceHover(pt: MasterAttendancePoint, i: number): void {
    this.hoveredAttendancePoint = pt;
    this.hoveredAttendanceIndex = i;
    this.cdr.detectChanges();
  }

  clearAttendanceHover(): void {
    this.hoveredAttendancePoint = null;
    this.hoveredAttendanceIndex = null;
    this.cdr.detectChanges();
  }

  getAttendanceTooltipLeft(x: number): number {
    return (x / 500) * 100;
  }

  // Distribution Hover Handlers
  setDeptHover(item: DepartmentDistributionItem, index: number): void {
    this.hoveredDeptIndex = index;
    this.hoveredDeptItem = item;
    this.cdr.detectChanges();
  }

  clearDeptHover(): void {
    this.hoveredDeptIndex = null;
    this.hoveredDeptItem = null;
    this.cdr.detectChanges();
  }

  // Hiring Hover Handlers
  setHiringHover(item: MonthlyHiringItem, index: number): void {
    this.hoveredHiringIndex = index;
    this.hoveredHiringItem = item;
    this.cdr.detectChanges();
  }

  clearHiringHover(): void {
    this.hoveredHiringIndex = null;
    this.hoveredHiringItem = null;
    this.cdr.detectChanges();
  }

  // Quick action dispatcher
  onQuickAction(action: string) {
    switch (action) {
      case 'add_employee':
        this.router.navigate(['/master-dashboard/employees'], { queryParams: { action: 'create' } });
        break;
      case 'approve_leave':
        this.activeCategoryTab = 'timeoff';
        this.activeOversightTab = 'pending';
        this.scrollToOversight();
        break;
      case 'mark_attendance':
        this.router.navigate(['/master-dashboard/attendance']);
        break;
      case 'run_payroll':
        this.showPayrollModal = true;
        break;
      case 'recruit_candidate':
        this.router.navigate(['/master-dashboard/employees']);
        break;
      case 'generate_report':
        this.router.navigate(['/master-dashboard/reports']);
        break;
    }
  }

  closePayrollModal() {
    this.showPayrollModal = false;
  }

  executePayroll() {
    alert('Payroll processing initiated successfully for the current cycle.');
    this.showPayrollModal = false;
  }

  scrollToOversight() {
    const el = document.getElementById('admin-oversight-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  }

  openPendingApprovalsTab(category: 'timeoff' | 'regularization') {
    this.activeCategoryTab = category;
    this.activeOversightTab = 'pending';
    this.scrollToOversight();
  }

  // Search & Tables
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

  // Approval oversight logic
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
        this.fetchAdminDashboard();
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
        this.fetchAdminDashboard();
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

