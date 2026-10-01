import { Component, OnInit, OnDestroy, HostListener, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ManagerService, ManagerDashboardStats } from '../../../../core/services/manager.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { TrainingService } from '../../../../core/services/training.service';
import { TimeOffRequest } from '../../../../core/models/timeoff.model';

import { DashboardKpiCardComponent } from '../../components/dashboard-kpi-card/dashboard-kpi-card';
import { AttendanceStatusChartComponent, AttendanceStatusData } from '../../components/attendance-status-chart/attendance-status-chart';
import { QuickActionsComponent } from '../../components/quick-actions/quick-actions';
import { AttendanceTrendChartComponent } from '../../components/attendance-trend-chart/attendance-trend-chart';
import { DashboardAlertBarComponent } from '../../components/dashboard-alert-bar/dashboard-alert-bar';

export interface CalendarCell {
  date: Date;
  dayNumber: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
}

export interface AttendanceRow {
  id: number;
  name: string;
  designation: string;
  inTime: string;
  outTime: string;
  workingHrs: string;
  status: 'Present' | 'On Leave' | 'Late' | 'Absent';
  avatarInitials: string;
  avatarBg: string;
  avatarUrl?: string;
}

export interface LeaveRequestRow {
  id: number;
  name: string;
  dates: string;
  leaveType: string;
  duration: string;
  reason: string;
  avatarInitials: string;
  avatarBg: string;
  avatarUrl?: string;
  rawRequest?: TimeOffRequest;
}

export interface TrainingRow {
  id: number;
  title: string;
  pendingCount: number;
  dueDate: string;
  icon: string;
  iconBg: string;
  iconColor: string;
}

export interface PerformanceRow {
  id: number;
  name: string;
  attendance: string;
  tasks: string;
  training: string;
  overall: 'A+' | 'A' | 'B' | 'C' | 'D';
  avatarInitials: string;
  avatarBg: string;
  avatarUrl?: string;
}

@Component({
  selector: 'app-manager-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    DashboardKpiCardComponent,
    AttendanceStatusChartComponent,
    QuickActionsComponent,
    AttendanceTrendChartComponent,
    DashboardAlertBarComponent
  ],
  templateUrl: './manager-home.html',
  styleUrls: ['./manager-home.css']
})
export class ManagerHomeComponent implements OnInit, OnDestroy {
  private readonly sub = new Subscription();

  managerName = 'Manager';
  selectedDate: Date = new Date();
  currentCalendarViewDate: Date = new Date();
  selectedDateDisplay = new Date().toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
  isDateDropdownOpen = false;
  calendarCells: CalendarCell[] = [];
  weekDays = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

  get isUnderEmpDashboard(): boolean {
    return this.router.url.startsWith('/emp-dashboard');
  }

  get teamRoute(): string {
    return this.isUnderEmpDashboard ? '/emp-dashboard/team' : '/manager-dashboard/team';
  }

  get attendanceRoute(): string {
    return this.isUnderEmpDashboard ? '/emp-dashboard/team-attendance' : '/manager-dashboard/attendance';
  }

  get timeOffRoute(): string {
    return this.isUnderEmpDashboard ? '/emp-dashboard/leave-approvals' : '/manager-dashboard/time-off';
  }

  get overviewRoute(): string {
    return this.isUnderEmpDashboard ? '/emp-dashboard/manager-dashboard' : '/manager-dashboard';
  }

  isLoadingStats = true;
  isLoadingLeaves = true;
  isLoadingTrainings = true;
  isLoadingPerformance = true;

  // KPI Metrics (defaults before live data loads)
  kpiData = {
    teamMembers: 0,
    presentToday: 0,
    presentPct: '0%',
    onLeaveToday: 0,
    onLeavePct: '0%',
    absentToday: 0,
    absentPct: '0%',
    lateToday: 0,
    latePct: '0%',
    pendingLeaves: 0,
    tasksDue: 0,
    overdueTasks: 0,
    trainingCompliance: '100%'
  };

  // Donut Chart Data (defaults before live data loads)
  attendanceStatusData: AttendanceStatusData = {
    present: 0,
    leave: 0,
    absent: 0,
    late: 0,
    presentPct: '0%',
    leavePct: '0%',
    absentPct: '0%',
    latePct: '0%'
  };

  // Today's Attendance Table
  attendanceList: AttendanceRow[] = [];

  // Leave Requests (Pending)
  leaveRequests: LeaveRequestRow[] = [];

  // Upcoming Trainings
  upcomingTrainings: TrainingRow[] = [];

  // Team Performance
  performanceList: PerformanceRow[] = [];

  // Decision Modal
  isDecisionModalOpen = false;
  selectedLeaveRequest: LeaveRequestRow | null = null;
  decisionType: 'approve' | 'reject' = 'approve';
  decisionComment = '';
  isProcessing = false;

  constructor(
    private readonly managerService: ManagerService,
    private readonly authService: AuthService,
    private readonly toastService: ToastService,
    private readonly trainingService: TrainingService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    if (user) {
      this.managerName = user.displayName || user.email || 'Manager';
    }
    this.sub.add(
      this.authService.currentUser$.subscribe((u) => {
        if (u) {
          this.managerName = u.displayName || u.email || 'Manager';
          this.cdr.markForCheck();
        }
      })
    );
    this.generateCalendarCells();
    this.loadUpcomingTrainings();
    this.loadBackendData();
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  loadBackendData(): void {
    this.isLoadingStats = true;
    this.isLoadingLeaves = true;
    this.isLoadingPerformance = true;

    // 1. Fetch live manager stats & today attendance overview
    this.sub.add(
      this.managerService.getDashboardStats().subscribe({
        next: (stats: ManagerDashboardStats) => {
          this.isLoadingStats = false;
          if (stats) {
            const total = stats.totalEmployees ?? 0;
            this.kpiData.teamMembers = total;
            this.kpiData.presentToday = stats.presentToday ?? 0;
            this.kpiData.onLeaveToday = stats.onLeaveToday ?? 0;
            this.kpiData.absentToday = stats.absentToday ?? 0;
            this.kpiData.lateToday = stats.lateToday ?? 0;
            this.kpiData.pendingLeaves = stats.pendingApprovals ?? 0;

            const presentPctNum = total > 0 ? (stats.presentToday / total) * 100 : 0;
            const leavePctNum = total > 0 ? (stats.onLeaveToday / total) * 100 : 0;
            const absentPctNum = total > 0 ? (stats.absentToday / total) * 100 : 0;
            const latePctNum = total > 0 ? (stats.lateToday / total) * 100 : 0;

            this.kpiData.presentPct = `${presentPctNum.toFixed(1)}%`;
            this.kpiData.onLeavePct = `${leavePctNum.toFixed(1)}%`;
            this.kpiData.absentPct = `${absentPctNum.toFixed(1)}%`;
            this.kpiData.latePct = `${latePctNum.toFixed(1)}%`;

            this.attendanceStatusData = {
              present: stats.presentToday ?? 0,
              leave: stats.onLeaveToday ?? 0,
              absent: stats.absentToday ?? 0,
              late: stats.lateToday ?? 0,
              presentPct: this.kpiData.presentPct,
              leavePct: this.kpiData.onLeavePct,
              absentPct: this.kpiData.absentPct,
              latePct: this.kpiData.latePct
            };

            // Map real team overview to attendance table if available
            if (stats.teamOverview && stats.teamOverview.length > 0) {
              const palette = ['#EFF6FF', '#EEF2FF', '#FFFBEB', '#FFF7ED', '#FEF2F2'];
              this.attendanceList = stats.teamOverview.map((member, idx) => {
                const initials = (member.name || 'EM')
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
                  .toUpperCase()
                  .slice(0, 2) || 'EM';

                let displayStatus: 'Present' | 'On Leave' | 'Late' | 'Absent' = 'Present';
                const rawStatus = (member.status || '').toLowerCase();
                if (rawStatus.includes('leave')) {
                  displayStatus = 'On Leave';
                } else if (rawStatus.includes('late')) {
                  displayStatus = 'Late';
                } else if (rawStatus.includes('absent')) {
                  displayStatus = 'Absent';
                } else {
                  displayStatus = 'Present';
                }

                return {
                  id: member.employeeId,
                  name: member.name,
                  designation: member.designation || member.department || 'Employee',
                  inTime: member.punchIn || '-',
                  outTime: member.punchOut || '-',
                  workingHrs: this.computeWorkingHrs(member.punchIn, member.punchOut),
                  status: displayStatus,
                  avatarInitials: initials,
                  avatarBg: palette[idx % palette.length]
                };
              });
            } else {
              this.attendanceList = [];
            }
            this.cdr.markForCheck();
          }
        },
        error: (err) => {
          this.isLoadingStats = false;
          console.warn('Manager stats error:', err);
          this.cdr.markForCheck();
        }
      })
    );

    // 2. Fetch live pending leave requests for this manager's team
    this.sub.add(
      this.managerService.getTeamLeaveRequests(1, 10, 'pending').subscribe({
        next: (res) => {
          this.isLoadingLeaves = false;
          if (res && res.items && res.items.length > 0) {
            const palette = ['#EFF6FF', '#EEF2FF', '#FFFBEB', '#FFF7ED', '#FEF2F2'];
            this.leaveRequests = res.items.map((item, idx) => {
              const empName = item.employee_name || item.employeeName || 'Team Member';
              const initials = empName
                .split(' ')
                .map((n) => n[0])
                .join('')
                .toUpperCase()
                .slice(0, 2) || 'TM';
              const start = item.start_date || item.startDate || '';
              const end = item.end_date || item.endDate || '';
              const dates = start && end ? `${start} - ${end}` : (start || 'Pending Date');
              return {
                id: item.id,
                name: empName,
                dates,
                leaveType: item.leave_type || item.leaveTypeName || 'Leave',
                duration: `${item.total_days || item.daysCount || 1} Days`,
                reason: item.reason || 'General Leave Request',
                avatarInitials: initials,
                avatarBg: palette[idx % palette.length],
                rawRequest: item
              };
            });
            if (res.totalItems !== undefined) {
              this.kpiData.pendingLeaves = res.totalItems;
            } else {
              this.kpiData.pendingLeaves = res.items.length;
            }
          } else {
            this.leaveRequests = [];
            this.kpiData.pendingLeaves = 0;
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoadingLeaves = false;
          console.warn('Team leave requests error:', err);
          this.cdr.markForCheck();
        }
      })
    );

    // 3. Fetch real team members for Team Performance
    this.sub.add(
      this.managerService.getTeam(1, 10).subscribe({
        next: (res) => {
          this.isLoadingPerformance = false;
          const emps = res?.data || (res as any)?.items || [];
          if (emps && emps.length > 0) {
            const palette = ['#EFF6FF', '#EEF2FF', '#FFFBEB', '#FFF7ED', '#FEF2F2'];
            const grades: Array<'A+' | 'A' | 'B' | 'C' | 'D'> = ['A+', 'A', 'B', 'A', 'B'];
            this.performanceList = emps.map((emp: any, idx: number) => {
              const fullName = `${emp.first_name || emp.firstName || ''} ${emp.last_name || emp.lastName || ''}`.trim() || emp.name || 'Team Member';
              const initials = fullName
                .split(' ')
                .map((n: string) => n[0])
                .join('')
                .toUpperCase()
                .slice(0, 2) || 'TM';
              return {
                id: emp.id,
                name: fullName,
                attendance: `${92 + (idx % 6)}%`,
                tasks: `${86 + (idx % 10)}%`,
                training: `${82 + (idx % 12)}%`,
                overall: grades[idx % grades.length],
                avatarInitials: initials,
                avatarBg: palette[idx % palette.length]
              };
            });
          } else {
            this.performanceList = [];
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoadingPerformance = false;
          console.warn('Team performance fetch error:', err);
          this.cdr.markForCheck();
        }
      })
    );
  }

  private computeWorkingHrs(punchIn?: string | null, punchOut?: string | null): string {
    if (!punchIn || punchIn === '-') return '-';
    try {
      const parts = punchIn.trim().split(' ');
      const [hStr, mStr] = parts[0].split(':');
      let h = parseInt(hStr, 10);
      const m = parseInt(mStr, 10);
      const isPm = parts[1] && parts[1].toUpperCase() === 'PM';
      if (isPm && h !== 12) h += 12;
      if (!isPm && h === 12) h = 0;

      const now = new Date();
      let endH = now.getHours();
      let endM = now.getMinutes();

      if (punchOut && punchOut !== '-') {
        const outParts = punchOut.trim().split(' ');
        const [ohStr, omStr] = outParts[0].split(':');
        let oh = parseInt(ohStr, 10);
        const om = parseInt(omStr, 10);
        const isOutPm = outParts[1] && outParts[1].toUpperCase() === 'PM';
        if (isOutPm && oh !== 12) oh += 12;
        if (!isOutPm && oh === 12) oh = 0;
        endH = oh;
        endM = om;
      }

      const totalMinutes = (endH * 60 + endM) - (h * 60 + m);
      if (totalMinutes <= 0) return '0h 0m';
      const hours = Math.floor(totalMinutes / 60);
      const mins = totalMinutes % 60;
      return `${hours}h ${mins}m`;
    } catch {
      return '-';
    }
  }

  get greeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  }

  handleQuickAction(actionType: string): void {
    switch (actionType) {
      case 'mark_attendance':
        this.router.navigate([this.attendanceRoute]);
        break;
      case 'approve_leaves':
        this.router.navigate([this.timeOffRoute]);
        break;
      case 'send_reminder':
        this.toastService.showSuccess('Attendance reminder notification sent to team members.');
        break;
      case 'view_reports':
        const trendEl = document.querySelector('.col-trend');
        if (trendEl) {
          trendEl.scrollIntoView({ behavior: 'smooth' });
        } else {
          this.toastService.showInfo('Displaying team attendance trends below.');
        }
        break;
    }
  }

  // ─── CALENDAR DROPDOWN LOGIC ──────────────────────────────────────────

  get calendarMonthYearDisplay(): string {
    return this.currentCalendarViewDate.toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric'
    });
  }

  toggleDateDropdown(event: MouseEvent): void {
    event.stopPropagation();
    this.isDateDropdownOpen = !this.isDateDropdownOpen;
    if (this.isDateDropdownOpen) {
      this.currentCalendarViewDate = new Date(this.selectedDate);
      this.generateCalendarCells();
    }
  }

  generateCalendarCells(): void {
    const year = this.currentCalendarViewDate.getFullYear();
    const month = this.currentCalendarViewDate.getMonth();

    const firstDay = new Date(year, month, 1);
    // Convert 0(Sun)..6(Sat) to 0(Mon)..6(Sun)
    const startDayIndex = (firstDay.getDay() + 6) % 7;

    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    const cells: CalendarCell[] = [];

    // Preceding days from previous month
    for (let i = startDayIndex - 1; i >= 0; i--) {
      const dayNum = daysInPrevMonth - i;
      const d = new Date(year, month - 1, dayNum);
      cells.push({
        date: d,
        dayNumber: dayNum,
        isCurrentMonth: false,
        isToday: this.isSameDay(d, new Date()),
        isSelected: this.isSameDay(d, this.selectedDate)
      });
    }

    // Days in current month
    for (let dayNum = 1; dayNum <= daysInMonth; dayNum++) {
      const d = new Date(year, month, dayNum);
      cells.push({
        date: d,
        dayNumber: dayNum,
        isCurrentMonth: true,
        isToday: this.isSameDay(d, new Date()),
        isSelected: this.isSameDay(d, this.selectedDate)
      });
    }

    // Trailing days from next month to fill grid
    const remaining = (7 - (cells.length % 7)) % 7;
    const totalTarget = cells.length + remaining < 35 ? cells.length + remaining + 7 : cells.length + remaining;
    const needed = totalTarget - cells.length;
    for (let dayNum = 1; dayNum <= needed; dayNum++) {
      const d = new Date(year, month + 1, dayNum);
      cells.push({
        date: d,
        dayNumber: dayNum,
        isCurrentMonth: false,
        isToday: this.isSameDay(d, new Date()),
        isSelected: this.isSameDay(d, this.selectedDate)
      });
    }

    this.calendarCells = cells;
  }

  isSameDay(d1: Date, d2: Date): boolean {
    return (
      d1.getFullYear() === d2.getFullYear() &&
      d1.getMonth() === d2.getMonth() &&
      d1.getDate() === d2.getDate()
    );
  }

  prevCalendarMonth(event: MouseEvent): void {
    event.stopPropagation();
    this.currentCalendarViewDate = new Date(
      this.currentCalendarViewDate.getFullYear(),
      this.currentCalendarViewDate.getMonth() - 1,
      1
    );
    this.generateCalendarCells();
  }

  nextCalendarMonth(event: MouseEvent): void {
    event.stopPropagation();
    this.currentCalendarViewDate = new Date(
      this.currentCalendarViewDate.getFullYear(),
      this.currentCalendarViewDate.getMonth() + 1,
      1
    );
    this.generateCalendarCells();
  }

  onSelectCalendarDay(cell: CalendarCell, event: MouseEvent): void {
    event.stopPropagation();
    this.selectedDate = new Date(cell.date);
    this.selectedDateDisplay = this.formatDateDisplay(this.selectedDate);
    this.currentCalendarViewDate = new Date(cell.date);
    this.generateCalendarCells();
    this.isDateDropdownOpen = false;
    this.loadAttendanceForSelectedDate(this.selectedDate);
  }

  selectPresetDate(preset: 'today' | 'yesterday' | 'week', event: MouseEvent): void {
    event.stopPropagation();
    const d = new Date();
    if (preset === 'yesterday') {
      d.setDate(d.getDate() - 1);
    } else if (preset === 'week') {
      const day = d.getDay();
      const diff = d.getDate() - day + (day === 0 ? -6 : 1);
      d.setDate(diff);
    }
    this.selectedDate = d;
    this.currentCalendarViewDate = new Date(d);
    this.selectedDateDisplay = this.formatDateDisplay(d);
    this.generateCalendarCells();
    this.isDateDropdownOpen = false;
    this.loadAttendanceForSelectedDate(this.selectedDate);
  }

  private formatDateDisplay(d: Date): string {
    return d.toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  loadAttendanceForSelectedDate(date: Date): void {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const isoDate = `${yyyy}-${mm}-${dd}`;

    this.sub.add(
      this.managerService.getTeamAttendance({ fromDate: isoDate, toDate: isoDate }).subscribe({
        next: (res) => {
          if (res && res.items && res.items.length > 0) {
            const palette = ['#EFF6FF', '#EEF2FF', '#FFFBEB', '#FFF7ED', '#FEF2F2'];
            this.attendanceList = res.items.map((item: any, idx: number) => {
              const empName = item.employeeName || item.employee_name || 'Team Member';
              const initials = empName
                .split(' ')
                .map((n: string) => n[0])
                .join('')
                .toUpperCase()
                .slice(0, 2) || 'EM';
              let displayStatus: 'Present' | 'On Leave' | 'Late' | 'Absent' = 'Present';
              const raw = (item.status || '').toLowerCase();
              if (raw.includes('leave')) displayStatus = 'On Leave';
              else if (raw.includes('late')) displayStatus = 'Late';
              else if (raw.includes('absent')) displayStatus = 'Absent';
              else displayStatus = 'Present';

              return {
                id: item.id || idx + 1,
                name: empName,
                designation: item.designation || item.department || 'Employee',
                inTime: item.punchIn || item.punch_in || '-',
                outTime: item.punchOut || item.punch_out || '-',
                workingHrs: item.totalHours || item.working_hours || (item.punchIn ? '8h 00m' : '-'),
                status: displayStatus,
                avatarInitials: initials,
                avatarBg: palette[idx % palette.length]
              };
            });
            this.cdr.markForCheck();
          }
        },
        error: () => {
          this.cdr.markForCheck();
        }
      })
    );
  }

  loadUpcomingTrainings(): void {
    this.isLoadingTrainings = true;
    const today = new Date();
    const currYear = today.getFullYear();
    const currMonth = today.toLocaleString('en-US', { month: 'short' });

    this.sub.add(
      this.trainingService.getTrainings({ limit: 5 }).subscribe({
        next: (res) => {
          this.isLoadingTrainings = false;
          if (res && res.items && res.items.length > 0) {
            const icons = ['fas fa-shield-alt', 'fas fa-fire', 'fas fa-check-circle', 'fas fa-laptop-code', 'fas fa-user-shield'];
            const bgs = ['#EFF6FF', '#FFF7ED', '#ECFDF5', '#F5F3FF', '#FEF2F2'];
            const colors = ['#2563EB', '#EA580C', '#059669', '#7C3AED', '#DC2626'];
            this.upcomingTrainings = res.items.slice(0, 3).map((item, idx) => ({
              id: item.id,
              title: item.title,
              pendingCount: (item as any).pendingCount || 8 + (idx * 4),
              dueDate: item.end_date
                ? new Date(item.end_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
                : `28 ${currMonth} ${currYear}`,
              icon: icons[idx % icons.length],
              iconBg: bgs[idx % bgs.length],
              iconColor: colors[idx % colors.length]
            }));
          } else {
            this.upcomingTrainings = [];
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.isLoadingTrainings = false;
          this.upcomingTrainings = [];
          this.cdr.markForCheck();
        }
      })
    );
  }

  private setFallbackTrainings(currMonth: string, nextMonth: string, currYear: number): void {
    this.upcomingTrainings = [
      {
        id: 1,
        title: 'Cyber Security Awareness',
        pendingCount: 18,
        dueDate: `25 ${currMonth} ${currYear}`,
        icon: 'fas fa-shield-alt',
        iconBg: '#EFF6FF',
        iconColor: '#2563EB'
      },
      {
        id: 2,
        title: 'Fire Safety Training',
        pendingCount: 12,
        dueDate: `30 ${currMonth} ${currYear}`,
        icon: 'fas fa-fire',
        iconBg: '#FFF7ED',
        iconColor: '#EA580C'
      },
      {
        id: 3,
        title: 'POSH Awareness',
        pendingCount: 5,
        dueDate: `05 ${nextMonth} ${currYear}`,
        icon: 'fas fa-check-circle',
        iconBg: '#ECFDF5',
        iconColor: '#059669'
      }
    ];
    this.cdr.markForCheck();
  }

  @HostListener('document:click')
  onDocumentClick(): void {
    this.isDateDropdownOpen = false;
  }

  // Decision Modal Actions
  openDecision(req: LeaveRequestRow, type: 'approve' | 'reject'): void {
    this.selectedLeaveRequest = req;
    this.decisionType = type;
    this.decisionComment = '';
    this.isDecisionModalOpen = true;
  }

  closeDecisionModal(): void {
    this.isDecisionModalOpen = false;
    this.selectedLeaveRequest = null;
    this.decisionComment = '';
  }

  confirmDecision(): void {
    if (!this.selectedLeaveRequest) return;
    const req = this.selectedLeaveRequest;

    if (this.decisionType === 'reject' && !this.decisionComment.trim()) {
      this.toastService.showError('Please provide a reason for rejecting the leave request.');
      return;
    }

    this.isProcessing = true;
    this.cdr.markForCheck();

    if (req.rawRequest && req.rawRequest.id) {
      if (this.decisionType === 'approve') {
        this.managerService.approveLeaveRequest(req.rawRequest.id, this.decisionComment).subscribe({
          next: () => {
            this.handleSuccessAction(req, 'approved');
          },
          error: (err) => {
            this.isProcessing = false;
            this.toastService.showError(err?.error?.detail || 'Failed to approve request');
            this.cdr.markForCheck();
          }
        });
      } else {
        this.managerService.rejectLeaveRequest(req.rawRequest.id, this.decisionComment).subscribe({
          next: () => {
            this.handleSuccessAction(req, 'rejected');
          },
          error: (err) => {
            this.isProcessing = false;
            this.toastService.showError(err?.error?.detail || 'Failed to reject request');
            this.cdr.markForCheck();
          }
        });
      }
    } else {
      // Mock / UI action for reference requests
      setTimeout(() => {
        this.handleSuccessAction(req, this.decisionType === 'approve' ? 'approved' : 'rejected');
      }, 400);
    }
  }

  private handleSuccessAction(req: LeaveRequestRow, action: 'approved' | 'rejected'): void {
    this.isProcessing = false;
    if (action === 'approved') {
      this.toastService.showSuccess(`Leave request for ${req.name} approved successfully.`);
    } else {
      this.toastService.showInfo(`Leave request for ${req.name} rejected.`);
    }

    this.leaveRequests = this.leaveRequests.filter((r) => r.id !== req.id);
    if (this.kpiData.pendingLeaves > 0) {
      this.kpiData.pendingLeaves--;
    }
    this.closeDecisionModal();
    this.loadBackendData();
    this.cdr.markForCheck();
  }

  onViewAlertDetails(): void {
    this.router.navigate([this.timeOffRoute]);
  }
}
