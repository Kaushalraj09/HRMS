import { Component, OnInit, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Navbar } from '../../../../shared/components/navbar/navbar';
import { MasterSidebar } from '../../components/master-sidebar/master-sidebar';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select/custom-select';
import { FooterComponent } from '../../../../shared/components/footer/footer';
import { filter } from 'rxjs/operators';
import { MasterSidebarService } from '../../components/master-sidebar/master-sidebar.service';
import { Subscription } from 'rxjs';

import { DashboardService } from '../../../../core/services/dashboard.service';
import { AdminDashboardData, DepartmentDistributionItem, MonthlyHiringItem, AttendanceOverviewPoint, RecentJoinerItem, BirthdayItem, PendingApprovalsSummary } from '../../../../core/models/dashboard.model';
import { AuthService } from '../../../../core/services/auth.service';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { RegularizationService } from '../../../../core/services/regularization.service';
import { groupTimeOffRequests } from '../../../../core/utils/timeoff-grouping.util';
import { GroupedTimeOffRequest } from '../../../../core/models/timeoff.model';

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

export interface SparklinePoint {
  x: number;
  y: number;
  val: number;
  dateStr: string;
  unit: string;
}

export interface SparklineResult {
  linePath: string;
  areaPath: string;
  points: SparklinePoint[];
  endX: number;
  endY: number;
}

@Component({
  selector: 'app-master-dashboard',
  imports: [MatFormFieldModule, MatSelectModule, CommonModule, FormsModule, Navbar, MasterSidebar, RouterModule, CustomSelectComponent, FooterComponent],
  standalone: true,
  templateUrl: './master-dashboard.html',
  styleUrl: './master-dashboard.css',
})
export class MasterDashboard implements OnInit, OnDestroy {
  attendanceFilterOptions: SelectOption[] = [
    { label: 'This Month', value: 'month' },
    { label: 'This Week', value: 'week' },
    { label: 'Today', value: 'today' }
  ];

  hiringFilterOptions: SelectOption[] = [
    { label: 'This Year', value: 'year' },
    { label: 'This Quarter', value: 'quarter' }
  ];
  selectedLang = 'en';
  isSidebarOpen$!: import('rxjs').Observable<boolean>;
  dashboardData: AdminDashboardData | null = null;
  userName = 'System Admin';
  dashboardError = '';
  isMainRoute = false;
  searchTerm = '';

  // Filter dropdown states
  selectedDateRange: string = '30d';
  isRefreshing: boolean = false;
  activeCardMenu: string | null = null;
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
  processedRegularizations: any[] = [];
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
    this.loadProcessedRegularizations();

    // WebSocket updates
    this.sub.add(
      this.timeoffService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
        this.loadPendingRegularizations();
        this.loadProcessedRegularizations();
        this.fetchAdminDashboard();
      })
    );
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }

  attendanceSplinePath: string = 'M 20 160 C 90 150, 120 70, 160 70 C 200 70, 220 140, 260 140 C 300 140, 320 60, 370 60 C 420 60, 440 25, 480 25';
  attendanceAreaPath: string = 'M 20 160 C 90 150, 120 70, 160 70 C 200 70, 220 140, 260 140 C 300 140, 320 60, 370 60 C 420 60, 440 25, 480 25 L 480 195 L 20 195 Z';

  fetchAdminDashboard() {
    this.isRefreshing = true;
    this.sub.add(
      this.dashboardService.getAdminDashboard(this.selectedDateRange).subscribe({
        next: (data) => {
          this.dashboardError = '';
          this.dashboardData = data;
          this.updateAttendancePointsFromData();
          this.isRefreshing = false;
          this.cdr.detectChanges();
        },
        error: (error) => {
          this.dashboardError = error?.error?.detail || 'Unable to load master dashboard data.';
          this.isRefreshing = false;
          this.cdr.detectChanges();
        }
      })
    );
  }

  private updateAttendancePointsFromData(): void {
    if (!this.dashboardData?.attendanceOverview || this.dashboardData.attendanceOverview.length === 0) {
      return;
    }

    const overview = this.dashboardData.attendanceOverview;
    const xCoords = [20, 135, 250, 365, 480];
    const topY = 25;
    const bottomY = 175;
    const yRange = bottomY - topY;

    const newPoints: MasterAttendancePoint[] = overview.map((pt, idx) => {
      const x = xCoords[idx] !== undefined ? xCoords[idx] : 20 + idx * 100;
      const normalizedPct = Math.max(0, Math.min(100, pt.percentage));
      // Invert Y: 100% is at topY (25), 0% is at bottomY (175)
      const y = Math.round(bottomY - (normalizedPct / 100) * yRange);
      let status = 'Working Day';
      if (normalizedPct === 0) status = 'Weekend / Not Marked';
      else if (normalizedPct >= 85) status = 'High Attendance';
      else if (normalizedPct >= 50) status = 'Moderate Attendance';

      return {
        label: pt.date,
        dateStr: `${pt.date} ${new Date().getFullYear()}`,
        pct: pt.percentage,
        x,
        y,
        presentCount: pt.present,
        totalCount: pt.total,
        status
      };
    });

    this.attendancePoints = newPoints;

    // Generate smooth SVG paths
    if (newPoints.length > 0) {
      let spline = `M ${newPoints[0].x} ${newPoints[0].y}`;
      for (let i = 1; i < newPoints.length; i++) {
        const p0 = newPoints[i - 1];
        const p1 = newPoints[i];
        const cx = Math.round((p0.x + p1.x) / 2);
        spline += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
      }
      const lastX = newPoints[newPoints.length - 1].x;
      const firstX = newPoints[0].x;
      this.attendanceSplinePath = spline;
      this.attendanceAreaPath = `${spline} L ${lastX} 195 L ${firstX} 195 Z`;
    }
  }

  onDateRangeChange(newRange: string) {
    this.selectedDateRange = newRange;
    this.fetchAdminDashboard();
  }

  refreshDashboard() {
    this.fetchAdminDashboard();
    this.loadPendingRequests();
    this.loadProcessedRequests();
    this.loadPendingRegularizations();
    this.loadProcessedRegularizations();
  }

  toggleCardMenu(cardName: string, event: MouseEvent) {
    event.stopPropagation();
    if (this.activeCardMenu === cardName) {
      this.activeCardMenu = null;
    } else {
      this.activeCardMenu = cardName;
    }
    this.cdr.detectChanges();
  }

  closeAllCardMenus() {
    if (this.activeCardMenu !== null) {
      this.activeCardMenu = null;
      this.cdr.detectChanges();
    }
  }

  attendanceGranularity = 'monthly';
  employeeGranularity = 'monthly';
  leaveGranularity = 'monthly';
  payrollGranularity = 'monthly';

  getGranularityLabel(g: string): string {
    if (g === 'weekly') return 'Weekly';
    if (g === 'monthly') return 'Monthly';
    if (g === 'quarterly') return 'Quarterly';
    if (g === 'yearly') return 'Yearly';
    return 'Monthly';
  }

  setAnalyticsGranularity(cardType: string, granularity: string): void {
    if (cardType === 'attendance') this.attendanceGranularity = granularity;
    else if (cardType === 'employees') this.employeeGranularity = granularity;
    else if (cardType === 'leaves') this.leaveGranularity = granularity;
    else if (cardType === 'payroll') this.payrollGranularity = granularity;

    this.selectedDateRange = granularity;
    this.fetchAdminDashboard();
    this.cdr.detectChanges();
  }

  onAnalyticsSelectChange(cardType: string, event: Event): void {
    event.stopPropagation();
    const target = event.target as HTMLSelectElement;
    const value = target?.value || 'monthly';
    this.onCardAction(cardType, 'analytics', undefined, value);
  }

  onCardAction(cardType: string, action: 'details' | 'analytics' | 'export', event?: MouseEvent, granularity?: string) {
    if (event) event.stopPropagation();
    this.activeCardMenu = null;

    if (granularity) {
      this.setAnalyticsGranularity(cardType, granularity);
    }

    if (action === 'details') {
      if (cardType === 'employees') this.router.navigate(['/master-dashboard/employees']);
      else if (cardType === 'attendance') this.router.navigate(['/master-dashboard/attendance']);
      else if (cardType === 'leaves') this.scrollToOversight();
      else if (cardType === 'payroll') this.showPayrollModal = true;
    } else if (action === 'analytics') {
      const targetId = `${cardType}-analytics-section`;
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    } else if (action === 'export') {
      this.exportCardData(cardType, granularity || this.selectedDateRange, 'pdf');
    }
  }

  exportCardData(cardType: string, granularity: string = 'monthly', format: string = 'pdf') {
    this.dashboardService.exportReport(cardType, granularity, format).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const ext = format === 'pdf' ? 'pdf' : 'csv';
        a.download = `${cardType}_report_${granularity}.${ext}`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        alert(`Failed to export ${cardType} report.`);
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

  // KPI Sparkline hover state
  hoveredKpiCard: 'employees' | 'attendance' | 'leaves' | 'payroll' | null = null;
  hoveredKpiPoint: SparklinePoint | null = null;
  hoveredKpiIndex: number | null = null;

  setKpiHover(card: 'employees' | 'attendance' | 'leaves' | 'payroll', pt: SparklinePoint, index: number, event?: MouseEvent): void {
    if (event) event.stopPropagation();
    this.hoveredKpiCard = card;
    this.hoveredKpiPoint = pt;
    this.hoveredKpiIndex = index;
    this.cdr.detectChanges();
  }

  clearKpiHover(): void {
    this.hoveredKpiCard = null;
    this.hoveredKpiPoint = null;
    this.hoveredKpiIndex = null;
    this.cdr.detectChanges();
  }

  generateSparkline(data: number[], unit = '', width = 200, height = 45, pad = 6): SparklineResult {
    if (!data || data.length < 2) {
      data = [0, 0, 0, 0, 0, 0, 0];
    }
    const minV = Math.min(...data);
    const maxV = Math.max(...data);
    const rangeV = maxV !== minV ? maxV - minV : 1.0;
    const n = data.length;

    const today = new Date();
    const pts: SparklinePoint[] = [];

    for (let i = 0; i < n; i++) {
      const x = Number(((i / (n - 1)) * width).toFixed(1));
      const y = Number(((height - pad) - ((data[i] - minV) / rangeV) * (height - 2 * pad)).toFixed(1));

      const d = new Date(today);
      d.setDate(today.getDate() - (n - 1 - i));
      const dateStr = d.toLocaleDateString('en-US', { day: '2-digit', month: 'short' });

      pts.push({
        x,
        y,
        val: data[i],
        dateStr,
        unit
      });
    }

    let linePath = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 1; i < pts.length; i++) {
      const p0 = pts[i - 1];
      const p1 = pts[i];
      const cx = Number(((p0.x + p1.x) / 2).toFixed(1));
      linePath += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
    }

    const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`;
    return {
      linePath,
      areaPath,
      points: pts,
      endX: pts[pts.length - 1].x,
      endY: pts[pts.length - 1].y
    };
  }

  get totalEmployeesSparkline(): SparklineResult {
    const raw = this.dashboardData?.headcountTrend || [3, 5, 5, 7, 7, 7, 7];
    return this.generateSparkline(raw, 'employees');
  }

  get attendanceSparkline(): SparklineResult {
    const raw = this.dashboardData?.attendanceTrend || [28.6, 57.1, 14.3, 71.4, 0.0, 28.6, 14.3];
    return this.generateSparkline(raw, '%');
  }

  get leaveSparkline(): SparklineResult {
    const raw = this.dashboardData?.leaveTrend || [0, 0, 0, 0, 0, 0, 0];
    return this.generateSparkline(raw, 'requests');
  }

  get payrollSparkline(): SparklineResult {
    const raw = this.dashboardData?.payrollTrend || [80, 85, 90, 95, 98, 99, 100];
    return this.generateSparkline(raw, '%');
  }

  get totalEmployeesDisplay(): string {
    const count = this.dashboardData?.totalEmployees ?? 6;
    return Number(count).toLocaleString('en-US');
  }

  get employeeGrowthText(): string {
    const count = this.dashboardData?.employeeGrowthCount ?? 6;
    const rate = this.dashboardData?.employeeGrowthRate ?? 1.46;
    return `${count} (${rate}%) this month`;
  }

  get attendanceRateDisplay(): string {
    const rate = this.dashboardData?.attendanceRate ?? 17;
    return `${Math.round(rate)}%`;
  }

  get attendanceGrowthText(): string {
    const rate = Math.abs(this.dashboardData?.attendanceGrowthRate ?? 4);
    return `${rate}% vs yesterday`;
  }

  get isAttendanceGrowthPositive(): boolean {
    return (this.dashboardData?.attendanceGrowthRate ?? 4) >= 0;
  }

  get pendingLeavesDisplay(): number {
    return this.dashboardData?.pendingLeavesCount ?? (this.pendingRequests.length + this.pendingRegularizations.length);
  }

  get payrollStatusDisplay(): string {
    return this.dashboardData?.payrollStatus || 'Completed';
  }

  get payrollPeriodDisplay(): string {
    return this.dashboardData?.payrollPeriod || 'For August 2026';
  }

  get departmentDistribution(): DepartmentDistributionItem[] {
    return this.dashboardData?.departmentDistribution || [];
  }

  get monthlyHiring(): MonthlyHiringItem[] {
    return this.dashboardData?.monthlyHiringTrend || [];
  }

  get recentJoiners(): RecentJoinerItem[] {
    return this.dashboardData?.recentJoiners || [];
  }

  get todayBirthdays(): BirthdayItem[] {
    return this.dashboardData?.todayBirthdays || [];
  }

  get pendingApprovalsSummary(): PendingApprovalsSummary {
    return this.dashboardData?.pendingApprovals || {
      leaveRequests: this.pendingRequests.length,
      timeOffRequests: 0,
      regularizationRequests: this.pendingRegularizations.length,
      expenseClaims: 0
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
      this.pendingRequests = groupTimeOffRequests(res.items || []);
      this.cdr.detectChanges();
    });
  }

  loadProcessedRequests() {
    this.timeoffService.getProcessedTimeOffRequests(1, 100).subscribe(res => {
      this.processedRequests = groupTimeOffRequests(res.items || []);
      this.cdr.detectChanges();
    });
  }

  formatHours(hours: number): string {
    if (hours === 0 || !hours) return '0h 0m';
    const totalMinutes = Math.round(hours * 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return `${h}h ${m}m`;
  }

  formatDuration(req: GroupedTimeOffRequest): string {
    if (req.leave_type === 'Full-Day' || req.leave_type === 'Full Day') {
      const days = req.requests.length;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    if (req.leave_type === 'Half-Day' || req.leave_type === 'Half Day') {
      const days = req.requests.length * 0.5;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    return this.formatHours(req.totalDurationHours);
  }

  processRequest(batchId: string, action: string) {
    const reqGroup = this.pendingRequests.find((r: any) => r.id === batchId);
    if (!reqGroup) return;

    let processedCount = 0;
    const reqIds = reqGroup.requests.map((r: any) => r.id);

    for (const rId of reqIds) {
      let approvedHours: number | undefined;
      if (action === 'APPROVE') {
        const r = reqGroup.requests.find((x: any) => x.id === rId);
        approvedHours = r?.duration_hours;
      }
      
      this.timeoffService.approveTimeOffRequest(rId, action as 'APPROVE' | 'REJECT', approvedHours).subscribe({
        next: () => {
          processedCount++;
          if (processedCount === reqIds.length) {
            alert(`Request ${action.toLowerCase()}d successfully`);
            this.loadPendingRequests();
            this.loadProcessedRequests();
            this.fetchAdminDashboard();
          }
        },
        error: (err) => {
          if (processedCount === 0) {
            alert(err?.error?.detail || "Error processing request");
          }
        }
      });
    }
  }

  viewRequestDetails(req: any): void {
    this.selectedRequest = req;
  }

  closeDetailsModal(): void {
    this.selectedRequest = null;
  }

  processRequestFromModal(batchId: string, action: string): void {
    this.processRequest(batchId, action);
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

  loadProcessedRegularizations() {
    this.regularizationService.getProcessedRequests(1, 100).subscribe(res => {
      this.processedRegularizations = res.items || [];
      this.cdr.detectChanges();
    });
  }

  processRegularization(requestId: number, status: 'approved' | 'rejected') {
    this.regularizationService.submitDecision(requestId, { status, reviewComment: 'Admin Oversight Decision' }).subscribe({
      next: () => {
        alert(`Regularization request ${status} successfully`);
        this.loadPendingRegularizations();
        this.loadProcessedRegularizations();
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

