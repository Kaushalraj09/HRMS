import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Navbar } from '../../../../shared/components/navbar/navbar';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { HrSidebarService } from '../../components/hr-sidebar/hr-sidebar.service';
import { FormsModule } from '@angular/forms';
import { HrSidebar } from '../../components/hr-sidebar/hr-sidebar';
import { DashboardService } from '../../../../core/services/dashboard.service';
import { WeeklyAttendanceTrendItem } from '../../../../core/models/dashboard.model';
import { AuthService } from '../../../../core/services/auth.service';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { EmployeeLocationMap } from '../../components/employee-location-map/employee-location-map';
import { RegularizationService } from '../../../../core/services/regularization.service';
import { MasterDataService } from '../../../../core/services/master-data.service';
import { DocumentService } from '../../../../core/services/document.service';

export interface DashboardKpiItem {
  id: string;
  label: string;
  value: string | number;
  change: string;
  isPositive: boolean;
  icon: string;
  iconBgClass: string;
  iconColorClass: string;
  sparklineD: string;
  sparklineColor: string;
}

export interface UpcomingEventItem {
  day: string;
  month: string;
  name: string;
  type: string;
  icon: string;
  iconBgClass: string;
  iconColorClass: string;
}

export interface HrQuickStatItem {
  value: string | number;
  label: string;
  icon: string;
  bgClass: string;
  iconClass: string;
  textClass: string;
}

export interface RecentAttendanceItem {
  name: string;
  employeeCode?: string;
  avatarUrl?: string;
  initials?: string;
  date: string;
  inTime: string;
  outTime: string;
  totalHours: string;
  status: string;
  department?: string;
  workMode?: string;
}

export interface LeaveRequestRow {
  id: number;
  name: string;
  initials: string;
  type: string;
  date: string;
  duration: string;
  status: string;
}

export interface WorkforceDataPoint {
  day: string;
  x: number;
  y: number;
  pct: number;
  present: number;
  absent: number;
  leave: number;
  wfh: number;
  total: number;
}

@Component({
  selector: 'app-hr-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatSelectModule,
    Navbar,
    RouterModule,
    HrSidebar,
    EmployeeLocationMap
  ],
  templateUrl: './hr-dashboard.html',
  styleUrls: ['./hr-dashboard.css'],
})
export class HrDashboard implements OnInit {
  isHrSidebarOpen$!: import('rxjs').Observable<boolean>;
  isDashboardHome: boolean = true;
  userName = 'System Admin';
  isAdmin = false;
  dashboardError = '';
  searchTerm = '';
  isDataLoading = false;

  // Filter toolbar state
  selectedDepartment = 'All Departments';
  selectedWorkMode = 'All Modes';
  selectedLocation = 'All Locations';
  selectedDateRange = 'Today';
  selectedMapFilter: string = 'ALL';

  setMapFilter(filter: string): void {
    if (this.selectedMapFilter === filter) {
      this.selectedMapFilter = 'ALL';
    } else {
      this.selectedMapFilter = filter;
    }
  }

  departmentOptions: string[] = ['All Departments'];
  workModeOptions: string[] = ['All Modes', 'Office', 'Remote', 'Field'];
  locationOptions: string[] = ['All Locations'];
  dateRangeOptions: string[] = ['Today', 'Yesterday', 'This Week', 'This Month'];

  // Top 6 KPI Metric Cards
  kpis: DashboardKpiItem[] = [
    {
      id: 'total',
      label: 'Total Employees',
      value: '0',
      change: '0% vs yesterday',
      isPositive: true,
      icon: 'fas fa-users',
      iconBgClass: 'bg-blue-50',
      iconColorClass: 'text-blue-600',
      sparklineD: 'M 0 16 Q 45 12 90 14 T 180 10',
      sparklineColor: '#2563EB'
    },
    {
      id: 'present',
      label: 'Present Today',
      value: '0',
      change: '0% vs yesterday',
      isPositive: true,
      icon: 'fas fa-user-check',
      iconBgClass: 'bg-emerald-50',
      iconColorClass: 'text-emerald-600',
      sparklineD: 'M 0 18 Q 45 10 90 14 T 180 8',
      sparklineColor: '#10B981'
    },
    {
      id: 'leave',
      label: 'On Leave',
      value: '0',
      change: '0% vs yesterday',
      isPositive: true,
      icon: 'fas fa-calendar-alt',
      iconBgClass: 'bg-amber-50',
      iconColorClass: 'text-amber-600',
      sparklineD: 'M 0 14 Q 45 18 90 12 T 180 14',
      sparklineColor: '#F59E0B'
    },
    {
      id: 'absent',
      label: 'Absent',
      value: '0',
      change: '0% vs yesterday',
      isPositive: false,
      icon: 'fas fa-user-times',
      iconBgClass: 'bg-rose-50',
      iconColorClass: 'text-rose-600',
      sparklineD: 'M 0 10 Q 45 6 90 14 T 180 16',
      sparklineColor: '#EF4444'
    },
    {
      id: 'late',
      label: 'Late Arrivals',
      value: '0',
      change: '0% vs yesterday',
      isPositive: true,
      icon: 'fas fa-clock',
      iconBgClass: 'bg-purple-50',
      iconColorClass: 'text-purple-600',
      sparklineD: 'M 0 16 Q 45 10 90 16 T 180 12',
      sparklineColor: '#8B5CF6'
    },
    {
      id: 'wfh',
      label: 'Work From Home',
      value: '0',
      change: '0% vs yesterday',
      isPositive: true,
      icon: 'fas fa-home',
      iconBgClass: 'bg-cyan-50',
      iconColorClass: 'text-cyan-600',
      sparklineD: 'M 0 18 Q 45 14 90 10 T 180 14',
      sparklineColor: '#06B6D4'
    }
  ];

  // Distribution Donut Charts
  locTotal = 0;
  locOffice = 0;
  locOfficePct = 0;
  locRemote = 0;
  locRemotePct = 0;
  locHybrid = 0;
  locHybridPct = 0;

  // Donut SVG arc calculations (Circumference = 301.6 for r=48)
  locCircumference = 301.6;
  locOfficeDashArray = '0 301.6';
  locOfficeOffset = 0;
  locRemoteDashArray = '0 301.6';
  locRemoteOffset = 0;
  locHybridDashArray = '0 301.6';
  locHybridOffset = 0;

  genderTotal = 0;
  genderMale = 0;
  genderMalePct = 0;
  genderFemale = 0;
  genderFemalePct = 0;
  genderMaleDashArray = '0 301.6';
  genderMaleOffset = 0;
  genderFemaleDashArray = '0 301.6';
  genderFemaleOffset = 0;

  // Upcoming Events
  upcomingEventsList: UpcomingEventItem[] = [];

  // Workforce Analytics
  workforcePeriod = 'This Week';
  wfPresent = 0;
  wfAttendanceRate = '0%';
  wfOnLeave = 0;
  wfWfh = 0;
  wfSplinePathD = 'M 20 80 L 440 80';
  wfGradientAreaD = 'M 20 80 L 440 80 L 440 90 L 20 90 Z';
  
  wfDataPoints: WorkforceDataPoint[] = [];
  hoveredWfPoint: WorkforceDataPoint | null = null;
  hoveredWfIndex: number | null = null;

  setWfHover(pt: WorkforceDataPoint, index: number): void {
    this.hoveredWfPoint = pt;
    this.hoveredWfIndex = index;
    this.cdr.detectChanges();
  }

  clearWfHover(): void {
    this.hoveredWfPoint = null;
    this.hoveredWfIndex = null;
    this.cdr.detectChanges();
  }

  getTooltipTop(ptY: number): number {
    const topPx = (ptY / 100) * 90;
    return Math.max(10, Math.round(topPx));
  }

  // HR Quick Stats (2x3 Grid)
  quickStatsList: HrQuickStatItem[] = [
    {
      value: '0',
      label: 'Total Employees',
      icon: 'fas fa-users',
      bgClass: 'quick-box-blue',
      iconClass: 'quick-ic-blue',
      textClass: 'text-blue-900'
    },
    {
      value: '0',
      label: 'Departments',
      icon: 'fas fa-building',
      bgClass: 'quick-box-green',
      iconClass: 'quick-ic-green',
      textClass: 'text-emerald-900'
    },
    {
      value: '0',
      label: 'Designations',
      icon: 'fas fa-id-badge',
      bgClass: 'quick-box-teal',
      iconClass: 'quick-ic-teal',
      textClass: 'text-teal-900'
    },
    {
      value: '0',
      label: 'Active Employees',
      icon: 'fas fa-user-check',
      bgClass: 'quick-box-purple',
      iconClass: 'quick-ic-purple',
      textClass: 'text-purple-900'
    },
    {
      value: '0',
      label: 'Pending Approvals',
      icon: 'fas fa-calendar-check',
      bgClass: 'quick-box-orange',
      iconClass: 'quick-ic-orange',
      textClass: 'text-amber-900'
    },
    {
      value: '0',
      label: 'HR Users',
      icon: 'fas fa-user-shield',
      bgClass: 'quick-box-yellow',
      iconClass: 'quick-ic-yellow',
      textClass: 'text-yellow-900'
    }
  ];

  // Row 4: Leave & Time-off Requests Table
  activeRequestTab: 'pending' | 'regularization' = 'pending';
  pendingTimeoffCount = 0;
  pendingRegularizationCount = 0;
  displayLeaveRequests: LeaveRequestRow[] = [];

  // Row 4: Recent Attendance Table
  displayRecentAttendance: RecentAttendanceItem[] = [];
  rawRecentTimeSheets: any[] = [];

  // Row 5: Employee Document Compliance & Latest News
  docComplianceRate = 0.0;
  docCompletedEmployees = 0;
  docPartialEmployees = 0;
  docAttentionEmployees = 0;
  docAttentionNote = 'Loading document compliance status...';
  totalRequiredDocs = 8;
  docCompletePct = 0;
  docPartialPct = 0;
  docAttentionPct = 0;

  latestNewsList = [
    {
      heading: 'Welcome to Aivan ERP System',
      contents: 'We are excited to announce the launch of our new ERP system designed to streamline your business operations and improve productivity.',
      newsType: 'GENERAL',
      typeClass: 'general-pill',
      date: 'April 10, 2026'
    },
    {
      heading: 'Welcome to New Branch opening',
      contents: 'We are excited to announce the launch of our new branch in downtown!',
      newsType: 'PROMOTIONAL',
      typeClass: 'promo-pill',
      date: 'April 10, 2026'
    }
  ];

  // Pending API Data
  pendingRequests: any[] = [];
  processedRequests: any[] = [];
  pendingRegularizations: any[] = [];
  weeklyTrendData: WeeklyAttendanceTrendItem[] = [];

  // Photo viewer modal state
  selectedPhotoUrl: string | null = null;
  selectedPhotoEmployeeName = '';

  constructor(
    private hrsidebarService: HrSidebarService,
    private router: Router,
    private readonly dashboardService: DashboardService,
    private readonly authService: AuthService,
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly regularizationService: RegularizationService,
    private readonly masterDataService: MasterDataService,
    private readonly documentService: DocumentService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isHrSidebarOpen$ = this.hrsidebarService.isHrSidebarOpen$;
    this.isDashboardHome = this.router.url.split('?')[0] === '/hr-dashboard';
    this.userName = this.authService.getDisplayName() || 'System Admin';

    this.router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.isDashboardHome = event.urlAfterRedirects.split('?')[0] === '/hr-dashboard';
        this.cdr.detectChanges();
      }
    });
  }

  ngOnInit() {
    const user = this.authService.getCurrentUser();
    this.isAdmin = user?.role === 'admin';

    this.loadMasterData();
    this.loadDashboardData();
    this.loadDocumentComplianceMetrics();
    this.loadPendingRequests();
    this.loadProcessedRequests();
    this.loadPendingRegularizations();

    if (user) {
      this.attendanceService.connectWebSocket(user.id);
    }

    this.timeoffService.timeoffUpdate$.subscribe(() => {
      this.loadDashboardData();
      this.loadDocumentComplianceMetrics();
      this.loadPendingRequests();
      this.loadProcessedRequests();
      this.loadPendingRegularizations();
    });

    this.attendanceService.wsMessage$.subscribe((msg: any) => {
      if (msg?.type === 'PUNCH_UPDATE' || msg?.type === 'ATTENDANCE_UPDATE' || msg?.type === 'NEW_NOTIFICATION') {
        this.loadDashboardData();
        this.loadDocumentComplianceMetrics();
        this.loadPendingRequests();
        this.loadProcessedRequests();
        this.loadPendingRegularizations();
      }
    });
  }

  loadDocumentComplianceMetrics(): void {
    this.documentService.getHrOverview().subscribe({
      next: (kpi) => {
        if (kpi) {
          const total = kpi.total_employees || 0;
          this.docCompletedEmployees = kpi.complete_employees || 0;
          this.docPartialEmployees = kpi.partial_employees || 0;
          this.docAttentionEmployees = kpi.attention_employees !== undefined ? kpi.attention_employees : Math.max(0, total - this.docCompletedEmployees);
          this.docComplianceRate = kpi.overall_compliance_rate || 0.0;
          this.totalRequiredDocs = kpi.total_required_docs || 8;

          if (total > 0) {
            this.docCompletePct = Math.round((this.docCompletedEmployees / total) * 100);
            this.docPartialPct = Math.round((this.docPartialEmployees / total) * 100);
            this.docAttentionPct = Math.max(0, 100 - this.docCompletePct - this.docPartialPct);
          } else {
            this.docCompletePct = 0;
            this.docPartialPct = 0;
            this.docAttentionPct = 0;
          }

          if (this.docAttentionEmployees > 0) {
            this.docAttentionNote = `${this.docAttentionEmployees} employee${this.docAttentionEmployees > 1 ? 's' : ''} require document attention`;
          } else if (total > 0) {
            this.docAttentionNote = 'All active employees have 100% compliant documents';
          } else {
            this.docAttentionNote = 'No active employees configured yet';
          }

          this.cdr.markForCheck();
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        console.warn('Failed to load document compliance metrics for HR dashboard:', err);
      }
    });
  }

  loadMasterData() {
    this.masterDataService.getBootstrapData().subscribe({
      next: (data) => {
        if (data.departments && data.departments.length > 0) {
          this.departmentOptions = ['All Departments', ...data.departments.map(d => d.name)];
          this.quickStatsList[1].value = data.departments.length;
        }
        if (data.designations && data.designations.length > 0) {
          this.quickStatsList[2].value = data.designations.length;
        }
        if (data.workLocations && data.workLocations.length > 0) {
          this.locationOptions = ['All Locations', ...data.workLocations.map(w => w.name || (w as any).city)];
        }
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error fetching master data:', err)
    });
  }

  loadDashboardData() {
    this.isDataLoading = true;
    this.dashboardService.getHrDashboard().subscribe({
      next: (data) => {
        this.dashboardError = '';
        const totalEmp = data.totalEmployees || 0;
        const presentEmp = data.presentEmployees || 0;
        const absentEmp = data.absentEmployees || 0;
        const checkedInEmp = data.checkedInEmployees || 0;

        this.kpis[0].value = totalEmp.toLocaleString();
        this.quickStatsList[0].value = totalEmp.toLocaleString();

        this.kpis[1].value = presentEmp.toLocaleString();
        this.wfPresent = presentEmp;

        this.kpis[2].value = ((data as any).onLeaveEmployees || 0).toLocaleString();
        this.wfOnLeave = (data as any).onLeaveEmployees || 0;

        this.kpis[3].value = absentEmp.toLocaleString();
        this.kpis[4].value = ((data as any).lateArrivals || 0).toLocaleString();

        // Work Mode Breakdown
        if (data.workModeBreakdown && data.workModeBreakdown.length >= 2) {
          this.locRemote = data.workModeBreakdown[0] || 0;
          this.locOffice = data.workModeBreakdown[1] || 0;
          if (data.workModeBreakdown.length >= 3) {
            this.locHybrid = data.workModeBreakdown[2] || 0;
            this.locTotal = this.locRemote + this.locOffice + this.locHybrid || totalEmp;
          } else {
            this.locTotal = totalEmp > 0 ? totalEmp : (this.locRemote + this.locOffice);
            this.locHybrid = Math.max(0, this.locTotal - this.locRemote - this.locOffice);
          }

          if (this.locTotal > 0) {
            this.locOfficePct = Math.round((this.locOffice / this.locTotal) * 100);
            this.locRemotePct = Math.round((this.locRemote / this.locTotal) * 100);
            this.locHybridPct = Math.max(0, 100 - this.locOfficePct - this.locRemotePct);
          } else {
            this.locOfficePct = 0;
            this.locRemotePct = 0;
            this.locHybridPct = 0;
          }

          this.kpis[5].value = this.locRemote.toLocaleString();
          this.calculateDonutOffsets();
        }

        // Gender Breakdown
        if (data.genderBreakdown && data.genderBreakdown.length >= 2) {
          this.genderFemale = data.genderBreakdown[0] || 0;
          this.genderMale = data.genderBreakdown[1] || 0;
          this.genderTotal = this.genderFemale + this.genderMale || totalEmp;
          
          if (this.genderTotal > 0) {
            this.genderMalePct = Math.round((this.genderMale / this.genderTotal) * 100);
            this.genderFemalePct = Math.max(0, 100 - this.genderMalePct);
          } else {
            this.genderMalePct = 0;
            this.genderFemalePct = 0;
          }
          
          this.calculateGenderOffsets();
        }

        // Quick Stats
        if (data.quickStats && data.quickStats.length > 0) {
          data.quickStats.forEach(stat => {
            if (stat.name === 'HR Users') this.quickStatsList[5].value = stat.total;
            if (stat.name === 'Departments') this.quickStatsList[1].value = stat.total;
            if (stat.name === 'Active Employees') this.quickStatsList[3].value = stat.total;
          });
        }

        // Weekly Attendance Trend & Analytics
        if (data.weeklyAttendanceTrend && data.weeklyAttendanceTrend.length > 0) {
          this.weeklyTrendData = data.weeklyAttendanceTrend;
          this.computeWeeklyTrendAnalytics(data.weeklyAttendanceTrend, totalEmp);
        }

        // Upcoming Events
        if (data.upcomingEvents && data.upcomingEvents.length > 0) {
          this.upcomingEventsList = data.upcomingEvents.map(ev => {
            const dateMatch = ev.note ? ev.note.match(/(?:Birthday:\s*)?([A-Za-z]+)\s*(\d{1,2})/i) : null;
            const month = dateMatch ? dateMatch[1].slice(0, 3).toUpperCase() : 'AUG';
            const day = dateMatch ? dateMatch[2] : '12';
            return {
              day,
              month,
              name: ev.name || 'Employee',
              type: ev.note?.includes('Birthday') ? 'Birthday' : 'Event',
              icon: ev.note?.includes('Birthday') ? 'fas fa-gift' : 'fas fa-flag',
              iconBgClass: ev.note?.includes('Birthday') ? 'bg-blue-50' : 'bg-emerald-50',
              iconColorClass: ev.note?.includes('Birthday') ? 'text-blue-600' : 'text-emerald-600'
            };
          });
        } else {
          this.upcomingEventsList = [
            { day: '15', month: 'AUG', name: 'Independence Day', type: 'Holiday', icon: 'fas fa-flag', iconBgClass: 'bg-emerald-50', iconColorClass: 'text-emerald-600' }
          ];
        }

        // Recent Timesheets
        if (data.recentTimeSheets && data.recentTimeSheets.length > 0) {
          this.rawRecentTimeSheets = data.recentTimeSheets;
          this.mapRecentAttendance(data.recentTimeSheets);
          
          // Late count calculation from real timesheets
          const lateCount = data.recentTimeSheets.filter((s: any) => s.status === 'Late' || (s.punchIn && s.punchIn > '09:30')).length;
          this.kpis[4].value = lateCount > 0 ? lateCount.toLocaleString() : (checkedInEmp > 0 ? Math.round(checkedInEmp * 0.1) : 0);
        }

        this.isDataLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error fetching HR dashboard data:', err);
        this.isDataLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  private calculateDonutOffsets() {
    const C = this.locCircumference;
    if (this.locTotal <= 0) {
      this.locOfficeDashArray = `0 ${C}`;
      this.locRemoteDashArray = `0 ${C}`;
      this.locHybridDashArray = `0 ${C}`;
      this.locOfficeOffset = 0;
      this.locRemoteOffset = 0;
      this.locHybridOffset = 0;
      return;
    }

    const officeArc = (this.locOfficePct / 100) * C;
    const remoteArc = (this.locRemotePct / 100) * C;
    const hybridArc = (this.locHybridPct / 100) * C;

    this.locOfficeDashArray = `${officeArc.toFixed(1)} ${C}`;
    this.locOfficeOffset = 0;

    this.locRemoteDashArray = `${remoteArc.toFixed(1)} ${C}`;
    this.locRemoteOffset = -officeArc;

    this.locHybridDashArray = `${hybridArc.toFixed(1)} ${C}`;
    this.locHybridOffset = -(officeArc + remoteArc);
  }

  private calculateGenderOffsets() {
    const C = this.locCircumference;
    if (this.genderTotal <= 0) {
      this.genderMaleDashArray = `0 ${C}`;
      this.genderFemaleDashArray = `0 ${C}`;
      this.genderMaleOffset = 0;
      this.genderFemaleOffset = 0;
      return;
    }

    const maleArc = (this.genderMalePct / 100) * C;
    const femaleArc = (this.genderFemalePct / 100) * C;

    this.genderMaleDashArray = `${maleArc.toFixed(1)} ${C}`;
    this.genderMaleOffset = 0;

    this.genderFemaleDashArray = `${femaleArc.toFixed(1)} ${C}`;
    this.genderFemaleOffset = -maleArc;
  }

  private computeWeeklyTrendAnalytics(trend: WeeklyAttendanceTrendItem[], totalEmp: number) {
    const len = trend.length;
    const latest = trend[len - 1];
    const prev = len >= 2 ? trend[len - 2] : latest;

    if (latest) {
      this.wfAttendanceRate = `${latest.percentage}%`;
      this.wfOnLeave = latest.leave || 0;
      this.wfWfh = latest.wfh || 0;
      this.kpis[2].value = this.wfOnLeave.toLocaleString();

      // Trend diffs vs yesterday
      const presentDiff = prev.present > 0 ? (((latest.present - prev.present) / prev.present) * 100).toFixed(1) : '0.0';
      const isPos = Number(presentDiff) >= 0;
      this.kpis[1].change = `${isPos ? '↑' : '↓'} ${Math.abs(Number(presentDiff))}% vs yesterday`;
      this.kpis[1].isPositive = isPos;

      const leaveDiff = prev.leave > 0 ? (((latest.leave - prev.leave) / prev.leave) * 100).toFixed(1) : '0.0';
      this.kpis[2].change = `${Number(leaveDiff) >= 0 ? '↑' : '↓'} ${Math.abs(Number(leaveDiff))}% vs yesterday`;

      const absentDiff = prev.absent > 0 ? (((latest.absent - prev.absent) / prev.absent) * 100).toFixed(1) : '0.0';
      this.kpis[3].change = `${Number(absentDiff) >= 0 ? '↑' : '↓'} ${Math.abs(Number(absentDiff))}% vs yesterday`;
      this.kpis[3].isPositive = Number(absentDiff) <= 0;
    }

    // Build 7 data points & Spline SVG Path
    const points: WorkforceDataPoint[] = [];
    const stepX = 420 / Math.max(1, len - 1);

    trend.forEach((item, i) => {
      const x = 20 + i * stepX;
      const pct = Math.min(100, Math.max(0, item.percentage || 0));
      // y-range: 15 (100%) to 85 (0%)
      const y = 85 - (pct / 100) * 70;
      points.push({
        day: item.date || `Day ${i + 1}`,
        x: Math.round(x),
        y: Math.round(y),
        pct: Math.round(pct),
        present: item.present ?? 0,
        absent: item.absent ?? 0,
        leave: item.leave ?? 0,
        wfh: item.wfh ?? 0,
        total: item.total ?? totalEmp
      });
    });

    this.wfDataPoints = points;
    if (points.length >= 2) {
      this.wfSplinePathD = this.buildSmoothPath(points);
      this.wfGradientAreaD = `${this.wfSplinePathD} L ${points[points.length - 1].x} 90 L ${points[0].x} 90 Z`;
    }
  }

  private buildSmoothPath(points: { x: number; y: number }[]): string {
    if (!points || points.length === 0) return '';
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i != points.length - 2 ? points[i + 2] : p2;

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${Math.round(cp1x)} ${Math.round(cp1y)}, ${Math.round(cp2x)} ${Math.round(cp2y)}, ${p2.x} ${p2.y}`;
    }
    return d;
  }

  loadPendingRequests() {
    this.timeoffService.getPendingTimeOffRequests(1, 20).subscribe(res => {
      this.pendingRequests = res.items || [];
      this.pendingTimeoffCount = (res as any).total || (res as any).totalItems || this.pendingRequests.length || 0;
      this.updatePendingApprovalsCount();

      if (this.activeRequestTab === 'pending') {
        this.displayLeaveRequests = this.pendingRequests.slice(0, 5).map(req => ({
          id: req.id,
          name: req.employee_name || 'Employee',
          initials: this.getInitials(req.employee_name || 'EM'),
          type: req.leave_type || 'Leave',
          date: req.date ? new Date(req.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Today',
          duration: req.duration_days ? `${req.duration_days} Day${req.duration_days > 1 ? 's' : ''}` : `${req.duration_hours || 1} Day`,
          status: req.status || 'Pending'
        }));
      }
      this.cdr.detectChanges();
    });
  }

  loadProcessedRequests() {
    this.timeoffService.getProcessedTimeOffRequests(1, 20).subscribe(res => {
      this.processedRequests = res.items || [];
      this.cdr.detectChanges();
    });
  }

  loadPendingRegularizations() {
    this.regularizationService.getPendingRequests(1, 20).subscribe(res => {
      this.pendingRegularizations = res.items || [];
      this.pendingRegularizationCount = (res as any).total || (res as any).totalItems || this.pendingRegularizations.length || 0;
      this.updatePendingApprovalsCount();

      if (this.activeRequestTab === 'regularization') {
        this.displayLeaveRequests = this.pendingRegularizations.slice(0, 5).map(req => ({
          id: req.id,
          name: req.employeeName || 'Employee',
          initials: this.getInitials(req.employeeName || 'EM'),
          type: 'Regularization',
          date: req.attendanceDate ? new Date(req.attendanceDate).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Today',
          duration: '-',
          status: req.status || 'Pending'
        }));
      }
      this.cdr.detectChanges();
    });
  }

  private updatePendingApprovalsCount() {
    this.quickStatsList[4].value = (this.pendingTimeoffCount + this.pendingRegularizationCount).toLocaleString();
  }

  mapRecentAttendance(sheets: any[]) {
    if (!sheets || sheets.length === 0) {
      this.displayRecentAttendance = [];
      return;
    }
    this.displayRecentAttendance = sheets.slice(0, 5).map(s => ({
      name: s.employee || 'Employee',
      employeeCode: s.employeeCode || '',
      initials: this.getInitials(s.employee || 'EM'),
      avatarUrl: s.punchInImage,
      date: s.date || 'Today',
      inTime: s.punchIn !== '-' ? s.punchIn : '09:30 AM',
      outTime: s.punchOut !== '-' ? s.punchOut : '-',
      totalHours: s.totalHours !== '-' ? s.totalHours : '0h 00m',
      status: s.status || 'Working',
      department: s.department,
      workMode: s.workMode
    }));
  }

  getInitials(name: string): string {
    if (!name) return 'EM';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  toggleSidebar() {
    this.hrsidebarService.toggleSidebar();
  }

  onSearch(term: string) {
    this.searchTerm = term || '';
    if (!this.searchTerm.trim()) {
      this.mapRecentAttendance(this.rawRecentTimeSheets);
      return;
    }
    const q = this.searchTerm.toLowerCase();
    const filtered = this.rawRecentTimeSheets.filter(s =>
      (s.employee && s.employee.toLowerCase().includes(q)) ||
      (s.employeeCode && s.employeeCode.toLowerCase().includes(q))
    );
    this.mapRecentAttendance(filtered);
  }

  openProfile() {
    this.router.navigate(['/hr-dashboard/my-profile']);
  }

  applyFilters() {
    let filtered = [...this.rawRecentTimeSheets];

    if (this.selectedDepartment !== 'All Departments') {
      filtered = filtered.filter(s => s.department === this.selectedDepartment);
    }
    if (this.selectedWorkMode !== 'All Modes') {
      filtered = filtered.filter(s => s.workMode?.toLowerCase() === this.selectedWorkMode.toLowerCase());
    }

    this.mapRecentAttendance(filtered);
  }

  resetFilters() {
    this.selectedDepartment = 'All Departments';
    this.selectedWorkMode = 'All Modes';
    this.selectedLocation = 'All Locations';
    this.selectedDateRange = 'Today';
    this.mapRecentAttendance(this.rawRecentTimeSheets);
  }

  setActiveRequestTab(tab: 'pending' | 'regularization') {
    this.activeRequestTab = tab;
    if (tab === 'regularization') {
      this.displayLeaveRequests = this.pendingRegularizations.slice(0, 5).map(req => ({
        id: req.id,
        name: req.employeeName || 'Employee',
        initials: this.getInitials(req.employeeName || 'EM'),
        type: 'Regularization',
        date: req.attendanceDate ? new Date(req.attendanceDate).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Today',
        duration: '-',
        status: req.status || 'Pending'
      }));
    } else {
      this.displayLeaveRequests = this.pendingRequests.slice(0, 5).map(req => ({
        id: req.id,
        name: req.employee_name || 'Employee',
        initials: this.getInitials(req.employee_name || 'EM'),
        type: req.leave_type || 'Leave',
        date: req.date ? new Date(req.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Today',
        duration: req.duration_days ? `${req.duration_days} Day${req.duration_days > 1 ? 's' : ''}` : `${req.duration_hours || 1} Day`,
        status: req.status || 'Pending'
      }));
    }
    this.cdr.detectChanges();
  }

  approveRequest(id: number) {
    if (this.activeRequestTab === 'regularization') {
      this.regularizationService.submitDecision(id, { status: 'approved', reviewComment: 'Approved via HR Dashboard' }).subscribe({
        next: () => {
          this.loadPendingRegularizations();
          this.loadDashboardData();
        },
        error: (err) => alert(err?.error?.detail || 'Error approving regularization request')
      });
    } else {
      this.timeoffService.approveTimeOffRequest(id, 'APPROVE').subscribe({
        next: () => {
          this.loadPendingRequests();
          this.loadDashboardData();
        },
        error: (err) => alert(err?.error?.detail || 'Error approving time-off request')
      });
    }
  }

  rejectRequest(id: number) {
    if (this.activeRequestTab === 'regularization') {
      this.regularizationService.submitDecision(id, { status: 'rejected', reviewComment: 'Rejected via HR Dashboard' }).subscribe({
        next: () => {
          this.loadPendingRegularizations();
          this.loadDashboardData();
        },
        error: (err) => alert(err?.error?.detail || 'Error rejecting regularization request')
      });
    } else {
      this.timeoffService.approveTimeOffRequest(id, 'REJECT').subscribe({
        next: () => {
          this.loadPendingRequests();
          this.loadDashboardData();
        },
        error: (err) => alert(err?.error?.detail || 'Error rejecting time-off request')
      });
    }
  }

  openPhotoModal(url: string, employeeName: string): void {
    this.selectedPhotoUrl = url;
    this.selectedPhotoEmployeeName = employeeName;
  }

  closePhotoModal(): void {
    this.selectedPhotoUrl = null;
    this.selectedPhotoEmployeeName = '';
  }
}
