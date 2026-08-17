import { CommonModule } from '@angular/common';
// Trigger dev server recompilation of dashboard component after modal import fix

import { ChangeDetectorRef, Component, Injectable, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CalendarModule, CalendarDateFormatter, CalendarNativeDateFormatter, DateFormatterParams } from 'angular-calendar';
import { CalendarEvent } from 'calendar-utils';
import { finalize, Subscription, interval, forkJoin, of } from 'rxjs';

import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TimeEngineService } from '../../../../core/services/time-engine.service';
import { MasterDataService } from '../../../../core/services/master-data.service';
import { Holiday } from '../../../../core/models/master-data.model';
import {
  EmployeeAttendanceSummaryItem,
  EmployeeTimelineEvent,
  EmployeeTimesheetRow,
  TodayAttendanceState,
  WorkMode
} from '../../../../core/models/attendance.model';
import {
  TimeSlotOption,
  buildHalfHourSlots,
  filterSlotsNotBeforeNow,
  hoursBetweenSameDay,
  parseTimeToMinutes,
  safeNumber,
  toIsoDateLocal
} from '../../../../core/utils/timeoff-time.util';
import {
  clampSeconds,
  formatSecondsToClock
} from '../../../../core/utils/attendance-time.util';
import { Navbar } from '../../../../shared/components/navbar/navbar';
import { EmpSidebar } from '../../components/emp-sidebar/emp-sidebar';
import { EmpSidebarService } from '../../components/emp-sidebar/emp-sidebar.service';

export interface DashboardCalendarDay {
  date: Date;
  isoDate: string;
  dayNumber: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  isSunday: boolean;
  isHoliday: boolean;
  isFuture: boolean;
  status: 'Present' | 'Leave' | 'Absent' | 'Holiday' | 'Not Marked' | 'WFH' | '';
  statusClass: 'present-day' | 'leave-day' | 'absent-day' | 'holiday-day' | 'not-marked-day' | 'wfh-day' | 'prev-month' | 'next-month' | '';
  statusLabel: string;
  title: string;
  punchIn?: string;
  punchOut?: string;
  workHours?: string;
  workMode?: string;
  leaveType?: string;
  holidayName?: string;
}

export interface DashboardRecentRequestItem {
  icon: string;
  iconBgClass: string;
  iconColorClass: string;
  title: string;
  date: string;
  type: string;
  status: 'Pending' | 'Approved' | 'Rejected' | string;
  statusClass: string;
}

export interface DashboardTimesheetDisplayRow {
  date: string;
  day: string;
  inTime: string;
  outTime: string;
  workHours: string;
  breakTime: string;
  overtime: string;
  status: string;
  statusClass: string;
}

export interface TrendDataPoint {
  day: string;
  dateStr: string;
  pct: number;
  x: number;
  y: number;
  label: string;
}

@Injectable()
export class CustomDateFormatter extends CalendarNativeDateFormatter {
  public override monthViewColumnHeader({ date, locale }: DateFormatterParams): string {
    return new Intl.DateTimeFormat(locale, { weekday: 'narrow' }).format(date);
  }
}

@Component({
  selector: 'app-emp-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatSelectModule,
    FormsModule,
    CalendarModule,
    Navbar,
    RouterModule,
    EmpSidebar
  ],
  templateUrl: './emp-dashboard.html',
  styleUrls: ['./emp-dashboard.css'],
  providers: [
    {
      provide: CalendarDateFormatter,
      useClass: CustomDateFormatter,
    },
  ],
})
export class EmpDashboard implements OnInit, OnDestroy {
  selectedLang = 'en';
  userName = 'Employee';
  currentDate = new Date();
  status: WorkMode = 'Office';
  isEmpSidebarOpen$!: import('rxjs').Observable<boolean>;
  isDashboardHome = true;
  isAdmin = false;
  searchTerm = '';

  isPunchedIn = false;
  punchInTime: string | null = null;
  punchOutTime: string | null = null;
  isPunchSaving = false;
  punchMessage = '';
  successMessage = '';
  attendanceStatusLabel = 'Not working';
  overtimeApproved = false;
  overtimeExtended = false;
  wsShiftEndReminderActive = false;
  wsOvertimeReminderActive = false;

  approvedHours = 0;
  remainingHours = 9;
  approvedSecondsToday = 0;
  remainingSecondsToday = 9 * 3600;
  totalWorkedSecondsToday = 0;
  shiftElapsedSeconds = 0;
  shiftProgress = 0;
  lateMinutes = 0;
  earlyLeaveMinutes = 0;
  overtimeMinutes = 0;

  shiftTotalHours = 9;
  shiftTotalSeconds = 9 * 3600;
  allTimeSlots: TimeSlotOption[] = [];

  recentTimeOffRequests: any[] = [];
  recentRequestsList: DashboardRecentRequestItem[] = [];

  readonly defaultRecentRequests: DashboardRecentRequestItem[] = [
    {
      icon: 'far fa-calendar-alt',
      iconBgClass: 'req-bg-blue',
      iconColorClass: 'req-ic-blue',
      title: 'Casual Leave',
      date: '12 Aug 2026',
      type: '1 Day',
      status: 'Pending',
      statusClass: 'pending-pill'
    },
    {
      icon: 'far fa-file-alt',
      iconBgClass: 'req-bg-purple',
      iconColorClass: 'req-ic-purple',
      title: 'Regularization',
      date: '08 Aug 2026',
      type: '-',
      status: 'Approved',
      statusClass: 'approved-pill'
    },
    {
      icon: 'far fa-calendar-minus',
      iconBgClass: 'req-bg-red',
      iconColorClass: 'req-ic-red',
      title: 'Work From Home',
      date: '05 Aug 2026',
      type: '1 Day',
      status: 'Rejected',
      statusClass: 'rejected-pill'
    },
    {
      icon: 'far fa-user',
      iconBgClass: 'req-bg-amber',
      iconColorClass: 'req-ic-amber',
      title: 'Sick Leave',
      date: '01 Aug 2026',
      type: '2 Days',
      status: 'Approved',
      statusClass: 'approved-pill'
    }
  ];

  pendingRequestsCount = 0;
  monthPresentDays = 0;
  monthTotalWorkingDays = 22;
  monthAttendancePercentage = 0;
  casualLeaveBalanceDays = 5;
  sickLeaveBalanceDays = 3;
  earnedLeaveBalanceDays = 4;
  leaveBalanceDays = 12;

  get totalAvailableLeaveDays(): number {
    return this.casualLeaveBalanceDays + this.sickLeaveBalanceDays + this.earnedLeaveBalanceDays;
  }

  formatTwoDigits(num: number): string {
    return num < 10 ? `0${num}` : `${num}`;
  }

  get isTodayWorkingDay(): boolean {
    const todayIso = toIsoDateLocal(new Date());
    const isSunday = new Date().getDay() === 0;
    const isHoliday = this.masterHolidays.some(h => h.date === todayIso && h.is_active !== false);
    return !isSunday && !isHoliday;
  }

  timeOffDate = toIsoDateLocal(new Date());
  timeOffLeaveType: 'Hourly' | 'Half Day' | 'Full Day' = 'Hourly';
  timeOffHalfDaySession: 'First Half' | 'Second Half' = 'First Half';
  timeOffStart = '09:00';
  timeOffEnd = '10:00';
  isTimeOffSubmitting = false;
  timeOffInlineError = '';
  timeOffInlineSuccess = '';

  timeSheets: EmployeeTimesheetRow[] = [];
  timeSheetPage = 1;
  readonly timeSheetPageSize = 10;
  attendanceSummary: EmployeeAttendanceSummaryItem[] = [];
  viewDate = new Date();
  selectedDate = new Date();
  weekNumber = 2;
  timelineEvents: EmployeeTimelineEvent[] = [];
  calendarEvents: CalendarEvent[] = [];
  calendarDays: DashboardCalendarDay[] = [];
  selectedEvents: EmployeeTimelineEvent[] = [];

  masterHolidays: Holiday[] = [];
  allTimesheets: EmployeeTimesheetRow[] = [];
  allTimeoffs: any[] = [];
  selectedCalendarDay: DashboardCalendarDay | null = null;
  selectedStatusFilter: string | null = null;
  calendarStatusCounts = { present: 0, leave: 0, absent: 0, holiday: 0, notMarked: 0, wfh: 0 };

  // Attendance Trend State
  trendPeriod: 'This Week' | 'Last Week' | 'This Month' = 'This Week';
  showTrendDropdown = false;
  trendAvgThisWeek = '82.4%';
  trendBestDay = '94.3%';
  trendBestDayName = 'Wed';
  trendLowestDay = '62.1%';
  trendLowestDayName = 'Fri';
  trendLinePathD = '';
  trendAreaPathD = '';
  trendDataPoints: TrendDataPoint[] = [];
  readonly defaultTrendPcts: number[] = [50.0, 55.0, 94.3, 72.5, 62.1, 65.0, 88.0];

  showScheduleModal = false;
  showTimeOffModal = false;
  scheduleForm = {
    date: new Date().toISOString().slice(0, 10),
    startTime: '09:00',
    workMode: 'Office' as WorkMode,
    taskDescription: ''
  };

  // ─── Camera / Photo Capture ───────────────────────────────────────
  showCameraModal = false;
  showSwitchConfirmModal = false;
  pendingWorkModeToSwitch: WorkMode = 'Office';
  public punchInImage: string | null = null;
  public punchOutImage: string | null = null;
  public punchInAddress: string | null = null;
  public punchOutAddress: string | null = null;
  public capturedImage: string | null = null;
  public cameraStream: MediaStream | null = null;
  public pendingPunchWorkMode: WorkMode = 'Office';
  public pendingPunchLatitude: number | undefined;
  public pendingPunchLongitude: number | undefined;
  public pendingPunchAddress: string | undefined;
  public isLocationLoading = false;

  latestNews_content = [
    {
      heading: 'Welcome to Aivan ERP System',
      contents: 'We are excited to announce the launch of our new ERP system designed to streamline your business operations and improve productivity.',
      newsType: 'General',
      date: new Date(2026, 3, 10)
    },
    {
      heading: 'Welcome to New Branch opening',
      contents: 'We are excited to announce the launch of our new branch in downtown!',
      newsType: 'Promotional',
      date: new Date(2026, 3, 10)
    },
  ];

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly empsidebarService: EmpSidebarService,
    private readonly router: Router,
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly authService: AuthService,
    private readonly timeEngine: TimeEngineService,
    private readonly masterDataService: MasterDataService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isEmpSidebarOpen$ = this.empsidebarService.isEmpSidebarOpen$;
    this.isDashboardHome = this.router.url.split('?')[0] === '/emp-dashboard';
    this.userName = this.authService.getDisplayName();

    this.subscriptions.add(
      this.router.events.subscribe((event) => {
        if (event instanceof NavigationEnd) {
          this.isDashboardHome = event.urlAfterRedirects.split('?')[0] === '/emp-dashboard';
          this.cdr.markForCheck();
        }
      })
    );

  }

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    this.isAdmin = user?.role === 'admin';

    this.subscriptions.add(
      this.timeEngine.state$.subscribe((state) => {
        if (!state) return;
        this.applyTodayState(state);
        this.cdr.markForCheck();
      })
    );

    this.initialize();
    this.startClock();
    this.updateAttendanceTrend();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  toggleSidebar() {
    this.empsidebarService.toggleSidebar();
  }

  onSearch(term: string) {
    this.searchTerm = term || '';
    this.timeSheetPage = 1;
    this.filterEvents(this.selectedDate);
  }

  openProfile() {
  }

  get punchActionLabel(): string {
    return this.isPunchedIn ? 'Punch Out' : 'Punch In';
  }

  get isPunchDisabled(): boolean {
    return this.isPunchSaving;
  }

  get liveTimerDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.totalWorkedSecondsToday);
  }

  get shiftElapsedDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.shiftElapsedSeconds);
  }

  get startTimeOptions(): TimeSlotOption[] {
    return filterSlotsNotBeforeNow(this.allTimeSlots, this.timeOffDate);
  }

  get endTimeOptions(): TimeSlotOption[] {
    if (this.timeOffLeaveType !== 'Hourly') {
      return [];
    }
    const startMin = parseTimeToMinutes(this.timeOffStart);
    return this.startTimeOptions.filter((option) => {
      const optionMinutes = parseTimeToMinutes(option.value);
      return optionMinutes !== null && startMin !== null && optionMinutes > startMin;
    });
  }

  get todayIsoMin(): string {
    return toIsoDateLocal(new Date());
  }

  get previewRequestedHours(): number {
    if (this.timeOffLeaveType === 'Full Day') {
      return this.shiftTotalHours;
    }
    if (this.timeOffLeaveType === 'Half Day') {
      return this.shiftTotalHours / 2;
    }
    return hoursBetweenSameDay(this.timeOffStart, this.timeOffEnd);
  }

  get previewRequestedSeconds(): number {
    if (this.timeOffLeaveType === 'Full Day') {
      return this.shiftTotalSeconds;
    }
    if (this.timeOffLeaveType === 'Half Day') {
      return (this.shiftTotalHours / 2) * 3600;
    }
    return clampSeconds(this.previewRequestedHours * 3600);
  }

  get previewRemainingAfterRequestSeconds(): number {
    return Math.max(0, this.remainingSecondsToday - this.previewRequestedSeconds);
  }

  get approvedHoursDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.approvedSecondsToday);
  }

  get remainingHoursDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.remainingSecondsToday);
  }

  get totalWorkedTodayDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.totalWorkedSecondsToday);
  }

  get requestedTimeDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.previewRequestedSeconds);
  }

  get previewRemainingAfterDisplay(): string {
    return this.timeEngine.formatHHMMSS(this.previewRemainingAfterRequestSeconds);
  }

  get lateDisplay(): string {
    return this.formatMinutesCompact(this.lateMinutes);
  }

  get earlyLeaveDisplay(): string {
    return this.formatMinutesCompact(this.earlyLeaveMinutes);
  }

  get overtimeDisplay(): string {
    return this.formatMinutesCompact(this.overtimeMinutes);
  }

  get isFutureDateSelected(): boolean {
    if (!this.timeOffDate) return false;
    const todayStr = this.toIsoDate(new Date());
    return this.timeOffDate > todayStr;
  }

  get canSubmitInlineTimeOff(): boolean {
    if (this.isTimeOffSubmitting) {
      return false;
    }
    if (this.isFutureDateSelected) {
      if (this.timeOffLeaveType === 'Hourly') {
        return this.previewRequestedSeconds > 0 && this.previewRequestedSeconds <= this.shiftTotalSeconds;
      }
      return true;
    }
    if (!this.isPunchedIn) {
      return false;
    }
    if (this.timeOffLeaveType === 'Full Day') {
      return this.remainingSecondsToday >= this.shiftTotalSeconds;
    }
    return this.previewRequestedSeconds > 0 && this.previewRequestedSeconds <= this.remainingSecondsToday;
  }

  get progressDashOffset(): number {
    const progress = Math.min(1, Math.max(0, this.shiftProgress));
    return 100 - Math.round(progress * 100);
  }

  get arcDashOffset(): number {
    const progress = Math.min(1, Math.max(0, this.shiftProgress));
    return Math.round(424 * (1 - progress));
  }

  get workProgressPercent(): number {
    const target = (this.shiftTotalHours || 9) * 3600;
    if (!target) return 0;
    return Math.min(100, Math.round((this.totalWorkedSecondsToday / target) * 100));
  }

  get greetingTime(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Morning';
    if (hour < 17) return 'Afternoon';
    return 'Evening';
  }

  get sortedTimeSheets(): EmployeeTimesheetRow[] {
    return [...this.timeSheets].sort((left, right) => {
      const dateDiff = new Date(right.date).getTime() - new Date(left.date).getTime();
      if (dateDiff !== 0) {
        return dateDiff;
      }

      return this.timeSortValue(right.entry) - this.timeSortValue(left.entry);
    });
  }

  get filteredTimeSheets(): EmployeeTimesheetRow[] {
    const query = this.searchTerm.trim().toLowerCase();
    if (!query) {
      return this.sortedTimeSheets;
    }

    return this.sortedTimeSheets.filter((row) => this.matchesSearch([
      row.date,
      row.day,
      row.scheduledStart,
      row.scheduledEnd,
      row.taskDescription,
      row.entry,
      row.exit,
      row.late,
      row.total,
      row.overtime,
      row.break,
      row.grandTotal,
      row.status
    ]));
  }

  get pagedTimeSheets(): EmployeeTimesheetRow[] {
    const start = (this.timeSheetPage - 1) * this.timeSheetPageSize;
    return this.filteredTimeSheets.slice(start, start + this.timeSheetPageSize);
  }

  get timeSheetTotalPages(): number {
    return Math.ceil(this.filteredTimeSheets.length / this.timeSheetPageSize);
  }

  get timeSheetPages(): number[] {
    return Array.from({ length: this.timeSheetTotalPages }, (_, index) => index + 1);
  }

  get timeSheetStartEntry(): number {
    return this.filteredTimeSheets.length > 0 ? ((this.timeSheetPage - 1) * this.timeSheetPageSize) + 1 : 0;
  }

  get timeSheetEndEntry(): number {
    return Math.min(this.timeSheetPage * this.timeSheetPageSize, this.filteredTimeSheets.length);
  }

  setTimeSheetPage(page: number): void {
    if (page < 1 || page > this.timeSheetTotalPages) {
      return;
    }

    this.timeSheetPage = page;
  }

  readonly defaultTimesheetRows: DashboardTimesheetDisplayRow[] = [
    {
      date: '11 Aug 2026',
      day: 'Tue',
      inTime: '09:32 AM',
      outTime: '08:41 PM',
      workHours: '08h 42m',
      breakTime: '01h 00m',
      overtime: '00h 12m',
      status: 'Working',
      statusClass: 'green-pill'
    },
    {
      date: '10 Aug 2026',
      day: 'Mon',
      inTime: '09:28 AM',
      outTime: '06:30 PM',
      workHours: '08h 02m',
      breakTime: '01h 00m',
      overtime: '00h 00m',
      status: 'Working',
      statusClass: 'green-pill'
    },
    {
      date: '09 Aug 2026',
      day: 'Sun',
      inTime: '-',
      outTime: '-',
      workHours: '-',
      breakTime: '-',
      overtime: '-',
      status: 'Holiday',
      statusClass: 'purple-pill'
    }
  ];

  get displayTimesheetRows(): DashboardTimesheetDisplayRow[] {
    if (!this.filteredTimeSheets || this.filteredTimeSheets.length === 0) {
      return this.defaultTimesheetRows;
    }

    return this.filteredTimeSheets.slice(0, 3).map((row) => {
      const d = row.date ? new Date(row.date) : new Date();
      const dateFormatted = isNaN(d.getTime())
        ? row.date
        : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      const dayFormatted = isNaN(d.getTime())
        ? (row.day || '')
        : d.toLocaleDateString('en-GB', { weekday: 'short' });

      const statusStr = String(row.status || '');
      const isWorking = statusStr === 'Working' || statusStr === 'Present';
      const isHoliday = statusStr === 'Holiday' || dayFormatted === 'Sun';
      const isAbsent = statusStr === 'Absent';
      const isTimeOff = statusStr === 'Time Off' || statusStr === 'Leave' || statusStr === 'Half Day';

      let statusClass = 'green-pill';
      let statusLabel = statusStr || 'Working';
      if (isHoliday) {
        statusClass = 'purple-pill';
        statusLabel = 'Holiday';
      } else if (isAbsent) {
        statusClass = 'red-pill';
        statusLabel = 'Absent';
      } else if (isTimeOff) {
        statusClass = 'orange-pill';
        statusLabel = 'Leave';
      } else if (isWorking) {
        statusClass = 'green-pill';
        statusLabel = 'Working';
      }

      return {
        date: dateFormatted,
        day: dayFormatted,
        inTime: this.formatTime12h(row.entry),
        outTime: this.formatTime12h(row.exit),
        workHours: this.formatDurationHm(row.total),
        breakTime: this.formatDurationHm(row.break) || '01h 00m',
        overtime: this.formatDurationHm(row.overtime) || '00h 00m',
        status: statusLabel,
        statusClass
      };
    });
  }

  formatTime12h(timeStr?: string): string {
    if (!timeStr || timeStr === '-' || timeStr === 'null' || timeStr.trim() === '') return '-';
    if (timeStr.includes('AM') || timeStr.includes('PM')) return timeStr;
    const parts = timeStr.split(':');
    if (parts.length < 2) return timeStr;
    let h = parseInt(parts[0], 10);
    const m = parts[1].slice(0, 2);
    if (isNaN(h)) return timeStr;
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12;
    if (h === 0) h = 12;
    const hStr = h < 10 ? `0${h}` : `${h}`;
    return `${hStr}:${m} ${ampm}`;
  }

  formatDurationHm(durStr?: string): string {
    if (!durStr || durStr === '-' || durStr === 'null' || durStr.trim() === '') return '-';
    if (durStr.includes('h') && durStr.includes('m')) return durStr;
    const parts = durStr.split(':');
    if (parts.length >= 2) {
      const h = parseInt(parts[0], 10) || 0;
      const m = parseInt(parts[1], 10) || 0;
      const hStr = h < 10 ? `0${h}` : `${h}`;
      const mStr = m < 10 ? `0${m}` : `${m}`;
      return `${hStr}h ${mStr}m`;
    }
    return durStr;
  }

  requestSwitchWorkMode(newMode: WorkMode): void {
    if (this.punchInTime !== null) {
      this.punchMessage = 'Working mode is locked after you have punched in for the day.';
      this.cdr.detectChanges();
      return;
    }
    if (this.status === newMode) {
      return;
    }
    this.pendingWorkModeToSwitch = newMode;
    this.showSwitchConfirmModal = true;
  }

  confirmSwitchWorkMode(): void {
    const targetMode = this.pendingWorkModeToSwitch;
    this.showSwitchConfirmModal = false;
    this.punchMessage = '';
    
    this.subscriptions.add(
      this.attendanceService.updateWorkMode(targetMode).subscribe({
        next: (todayState) => {
          this.applyTodayState(todayState);
          this.loadDashboardData();
          this.cdr.detectChanges();
        },
        error: (error) => {
          const detail = error?.error?.detail;
          this.punchMessage = typeof detail === 'string' ? detail : 'Unable to update work mode.';
          this.cdr.detectChanges();
        }
      })
    );
  }

  closeSwitchConfirmModal(): void {
    this.showSwitchConfirmModal = false;
  }

  togglePunch(): void {
    if (this.isPunchDisabled) {
      return;
    }
    this.punchMessage = '';
    this.pendingPunchWorkMode = this.status;
    this.pendingPunchLatitude = undefined;
    this.pendingPunchLongitude = undefined;
    this.pendingPunchAddress = '';

    this.openCameraModal();
    this.fetchCurrentLocation();
  }

  fetchCurrentLocation(): void {
    this.isLocationLoading = true;
    if (!this.pendingPunchAddress) {
      this.pendingPunchAddress = 'AiVan 360 Office, Delhi';
    }
    this.cdr.detectChanges();

    const fallbackToIp = () => {
      this.subscriptions.add(
        this.attendanceService.getIpLocation().subscribe({
          next: (res: any) => {
            if (res && res.latitude && res.longitude) {
              this.pendingPunchLatitude = res.latitude;
              this.pendingPunchLongitude = res.longitude;
              
              const city = res.cityName || '';
              const region = res.regionName || '';
              const country = res.countryName || '';
              const loc = [city, region, country].filter(val => !!val).join(', ');
              if (loc) {
                this.pendingPunchAddress = loc;
              }
            }
            this.isLocationLoading = false;
            this.cdr.detectChanges();
          },
          error: () => {
            this.isLocationLoading = false;
            this.cdr.detectChanges();
          }
        })
      );
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.pendingPunchLatitude = pos.coords.latitude;
          this.pendingPunchLongitude = pos.coords.longitude;
          this.attendanceService.reverseGeocode(pos.coords.latitude, pos.coords.longitude).subscribe({
            next: (geo: any) => {
              if (geo?.display_name) {
                this.pendingPunchAddress = geo.display_name;
              }
              this.isLocationLoading = false;
              this.cdr.detectChanges();
            },
            error: () => {
              fallbackToIp();
            }
          });
        },
        () => {
          fallbackToIp();
        },
        { enableHighAccuracy: false, timeout: 3000, maximumAge: 60000 }
      );
    } else {
      fallbackToIp();
    }
  }

  refetchLocation(): void {
    this.pendingPunchAddress = '';
    this.pendingPunchLatitude = undefined;
    this.pendingPunchLongitude = undefined;
    this.fetchCurrentLocation();
  }

  onAddressManualEdit(): void {
    this.pendingPunchLatitude = undefined;
    this.pendingPunchLongitude = undefined;
  }

  openCameraModal(): void {
    this.capturedImage = null;
    this.punchMessage = '';
    this.showCameraModal = true;
    this.cdr.detectChanges();
    if (!this.isPunchedIn) {
      setTimeout(() => this.startCamera(), 200);
    }
  }

  private startCamera(): void {
    const video = document.getElementById('cameraFeed') as HTMLVideoElement | null;
    if (!video) return;
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      .then(stream => {
        this.cameraStream = stream;
        video.srcObject = stream;
        video.play();
      })
      .catch(() => {
        console.warn('Camera permission denied or camera unavailable');
        this.capturedImage = null;
        this.cdr.detectChanges();
      });
  }

  private capturePhotoProgrammatically(video: HTMLVideoElement): string | null {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 320;
      canvas.height = video.videoHeight || 240;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        this.capturedImage = canvas.toDataURL('image/jpeg', 0.75);
        return this.capturedImage;
      }
    } catch (e) {
      console.error('Error capturing background photo:', e);
    }
    return null;
  }

  confirmPhoto(image: string | null = this.capturedImage): void {
    if (!this.isPunchedIn && !image) {
      const video = document.getElementById('cameraFeed') as HTMLVideoElement | null;
      image = video ? this.capturePhotoProgrammatically(video) : null;
    }
    this.executePunch(this.isPunchedIn ? null : image);
  }

  closeCameraModal(): void {
    this.stopCamera();
    this.showCameraModal = false;
    this.capturedImage = null;
    this.cdr.detectChanges();
  }

  private stopCamera(): void {
    this.cameraStream?.getTracks().forEach(t => t.stop());
    this.cameraStream = null;
  }

  private executePunch(image: string | null): void {
    this.isPunchSaving = true;
    this.punchMessage = '';
    this.cdr.detectChanges();

    const request$ = this.isPunchedIn
      ? this.attendanceService.punchOut(
          this.pendingPunchWorkMode,
          this.pendingPunchLatitude,
          this.pendingPunchLongitude,
          this.pendingPunchAddress,
          image
        )
      : this.attendanceService.punchIn(
          this.pendingPunchWorkMode,
          this.pendingPunchLatitude,
          this.pendingPunchLongitude,
          this.pendingPunchAddress,
          image
        );

    this.subscriptions.add(
      request$
        .pipe(finalize(() => {
          this.isPunchSaving = false;
          this.cdr.detectChanges();
        }))
        .subscribe({
          next: (todayState: TodayAttendanceState) => {
            this.closeCameraModal();
            this.applyTodayState(todayState);
            this.loadDashboardData();
            this.punchMessage = '';
            this.cdr.detectChanges();
          },
          error: (error) => {
            const detail = error?.error?.detail;
            if (typeof detail === 'object' && detail !== null && detail.message) {
              this.punchMessage = detail.message;
            } else {
              this.punchMessage = typeof detail === 'string' ? detail : 'Unable to update attendance right now.';
            }
            this.cdr.detectChanges();
          }
        })
    );
  }

  formatTime12to24(time12: string): string {
    if (!time12) return '';
    const parts = time12.match(/(\d+):(\d+)\s*(AM|PM)/i);
    if (!parts) return time12.substring(0, 5);
    let h = parseInt(parts[1], 10);
    const m = parts[2];
    if (parts[3].toUpperCase() === 'PM' && h < 12) h += 12;
    if (parts[3].toUpperCase() === 'AM' && h === 12) h = 0;
    return `${h.toString().padStart(2, '0')}:${m}`;
  }

  onLeaveTypeChange(): void {
    this.timeOffInlineError = '';
    const start24 = this.formatTime12to24(this.shiftStart) || '09:00';
    const end24 = this.formatTime12to24(this.shiftEnd) || '18:00';
    const lunch24 = this.formatTime12to24(this.lunchStart) || '13:00';

    if (this.timeOffLeaveType === 'Full Day') {
      this.timeOffStart = start24;
      this.timeOffEnd = end24;
    } else if (this.timeOffLeaveType === 'Half Day') {
      this.timeOffHalfDaySession = 'First Half';
      this.timeOffStart = start24;
      this.timeOffEnd = lunch24;
    } else {
      this.timeOffStart = start24;
      // Add one hour
      let h = parseInt(start24.split(':')[0], 10) + 1;
      this.timeOffEnd = `${h.toString().padStart(2, '0')}:${start24.split(':')[1]}`;
    }
  }

  onHalfDaySessionChange(): void {
    this.timeOffInlineError = '';
    const start24 = this.formatTime12to24(this.shiftStart) || '09:00';
    const end24 = this.formatTime12to24(this.shiftEnd) || '18:00';
    const lunch24 = this.formatTime12to24(this.lunchStart) || '13:00';
    const postLunch24 = this.formatTime12to24(this.lunchEnd) || '14:00';

    if (this.timeOffHalfDaySession === 'First Half') {
      this.timeOffStart = start24;
      this.timeOffEnd = lunch24;
    } else {
      this.timeOffStart = postLunch24;
      this.timeOffEnd = end24;
    }
  }

  onTimeOffDateChange(): void {
    this.timeOffInlineError = '';
    this.ensureTimeSelectionsValid();
  }

  onStartTimeChange(): void {
    const endOptions = this.endTimeOptions;
    if (endOptions.length && !endOptions.some((option) => option.value === this.timeOffEnd)) {
      this.timeOffEnd = endOptions[0].value;
    }
  }

  submitInlineTimeOff(): void {
    this.timeOffInlineError = '';
    this.timeOffInlineSuccess = '';
    if (!this.canSubmitInlineTimeOff) {
      this.timeOffInlineError = this.isFutureDateSelected
        ? 'Invalid requested time duration.'
        : (this.isPunchedIn
            ? 'Requested time must fit inside your remaining shift balance.'
            : 'You can apply time off only while marked as Working.');
      return;
    }

    this.isTimeOffSubmitting = true;

    let leaveTypeBackend = 'Hourly';
    let startTimeBackend: string | null = this.timeOffStart;
    let endTimeBackend: string | null = this.timeOffEnd;

    if (this.timeOffLeaveType === 'Full Day') {
      leaveTypeBackend = 'Full-Day';
      startTimeBackend = null;
      endTimeBackend = null;
    } else if (this.timeOffLeaveType === 'Half Day') {
      leaveTypeBackend = 'Half-Day';
      const start24 = this.formatTime12to24(this.shiftStart) || '09:00';
      const end24 = this.formatTime12to24(this.shiftEnd) || '18:00';
      const lunch24 = this.formatTime12to24(this.lunchStart) || '13:00';
      const postLunch24 = this.formatTime12to24(this.lunchEnd) || '14:00';

      if (this.timeOffHalfDaySession === 'First Half') {
        startTimeBackend = start24;
        endTimeBackend = lunch24;
      } else {
        startTimeBackend = postLunch24;
        endTimeBackend = end24;
      }
    }

    this.subscriptions.add(
      this.timeoffService
        .requestTimeOff(
          this.timeOffDate,
          leaveTypeBackend,
          startTimeBackend,
          endTimeBackend,
          this.timeOffLeaveType === 'Full Day' ? 9.0 : (this.timeOffLeaveType === 'Half Day' ? 4.0 : this.previewRequestedSeconds / 3600)
        )
        .pipe(finalize(() => { this.isTimeOffSubmitting = false; }))
        .subscribe({
          next: () => {
            this.timeOffInlineSuccess = 'Time off request submitted for manager/HR approval.';
            this.loadDashboardData();
            this.cdr.detectChanges();
            
            // Clear success message after 5 seconds
            setTimeout(() => {
              this.timeOffInlineSuccess = '';
              this.cdr.detectChanges();
            }, 5000);
          },
          error: (error) => {
            const detail = error?.error?.detail;
            this.timeOffInlineError = typeof detail === 'string' ? detail : 'Could not submit time off.';
            this.cdr.detectChanges();
          }
        })
    );
  }

  openScheduleModal() {
    this.scheduleForm.date = this.toIsoDate(this.selectedDate);
    this.showScheduleModal = true;
  }

  closeScheduleModal() {
    this.showScheduleModal = false;
  }

  saveSchedule() {
    this.subscriptions.add(
      this.attendanceService.addSchedule(
        this.scheduleForm.date,
        this.scheduleForm.workMode,
        this.scheduleForm.taskDescription,
        this.scheduleForm.startTime
      ).subscribe(() => {
        this.showScheduleModal = false;
        this.loadDashboardData();
      })
    );
  }

  onDayClick(day: { date: Date }) {
    this.selectedDate = day.date;
    this.weekNumber = this.getWeekOfMonth(day.date);
    this.timeOffDate = this.toIsoDate(day.date);
    this.ensureTimeSelectionsValid();
    this.filterEvents(day.date);

    const match = this.calendarDays.find(d => d.isoDate === this.toIsoDate(day.date));
    if (match) {
      this.onSelectCalendarDay(match);
    }
  }

  getMonthName(monthIndex: number): string {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[monthIndex] || '';
  }

  get isSelectedDateToday(): boolean {
    if (!this.selectedDate) return true;
    return toIsoDateLocal(this.selectedDate) === toIsoDateLocal(new Date());
  }

  onSelectCalendarDay(day: DashboardCalendarDay): void {
    if (!day) return;
    this.calendarDays.forEach(d => d.isSelected = false);
    day.isSelected = true;
    this.selectedCalendarDay = day;
    this.selectedDate = day.date;
    this.timeOffDate = day.isoDate;
    this.weekNumber = this.getWeekOfMonth(day.date);
    this.ensureTimeSelectionsValid();
    this.filterEvents(day.date);
    this.cdr.detectChanges();
  }

  toggleStatusFilter(status: string): void {
    if (this.selectedStatusFilter === status) {
      this.selectedStatusFilter = null;
    } else {
      this.selectedStatusFilter = status;
    }
    this.cdr.detectChanges();
  }

  goToToday(): void {
    this.viewDate = new Date();
    this.selectedDate = new Date();
    this.generateCalendar();
    const todayMatch = this.calendarDays.find(d => d.isToday && d.isCurrentMonth);
    if (todayMatch) {
      this.onSelectCalendarDay(todayMatch);
    }
    this.cdr.detectChanges();
  }

  getWeekOfMonth(date: Date): number {
    const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
    const dayOfWeek = firstDayOfMonth.getDay();
    return Math.ceil((date.getDate() + dayOfWeek) / 7);
  }

  filterEvents(date: Date) {
    const isoDate = this.toIsoDate(date);
    this.selectedEvents = this.timelineEvents
      .filter((event) => event.date === isoDate && this.matchesSearch([
        event.date,
        event.time,
        event.title,
        event.location,
        event.taskDescription
      ]))
      .sort((left, right) => this.eventSortValue(left.time) - this.eventSortValue(right.time));
  }

  get filteredLatestNews() {
    return this.latestNews_content.filter((item) => this.matchesSearch([
      item.heading,
      item.contents,
      item.newsType,
      item.date ? new Date(item.date).toDateString() : ''
    ]));
  }

  private initialize(): void {
    this.weekNumber = this.getWeekOfMonth(this.selectedDate);
    this.updateRecentRequests();
    this.loadDashboardData();

    const user = this.authService.getCurrentUser();
    if (user) {
      this.attendanceService.connectWebSocket(user.id);
      this.subscriptions.add(
        this.attendanceService.wsMessage$.subscribe((msg) => {
          if (msg && msg.type === 'SHIFT_END_REMINDER') {
            this.wsShiftEndReminderActive = true;
            this.cdr.detectChanges();
          } else if (msg && msg.type === 'OVERTIME_REMINDER') {
            this.wsOvertimeReminderActive = true;
            this.cdr.detectChanges();
          } else if (msg && msg.type === 'AUTO_CHECKOUT') {
            this.loadDashboardData();
          }
        })
      );
    }
  }

  updateRecentRequests(): void {
    if (!this.allTimeoffs || this.allTimeoffs.length === 0) {
      this.recentRequestsList = [...this.defaultRecentRequests];
      return;
    }

    const mapped: DashboardRecentRequestItem[] = this.allTimeoffs.slice(0, 4).map((req: any) => {
      const isPending = req.status === 'Pending';
      const isApproved = ['Approved', 'Completed', 'Active'].includes(req.status);
      const isRejected = ['Rejected', 'Cancelled', 'Expired'].includes(req.status);
      
      let icon = 'far fa-calendar-alt';
      let iconBgClass = 'req-bg-blue';
      let iconColorClass = 'req-ic-blue';
      
      const typeLower = (req.leave_type || '').toLowerCase();
      if (typeLower.includes('regular') || typeLower.includes('missed')) {
        icon = 'far fa-file-alt';
        iconBgClass = 'req-bg-purple';
        iconColorClass = 'req-ic-purple';
      } else if (typeLower.includes('home') || typeLower.includes('wfh') || typeLower.includes('remote')) {
        icon = 'far fa-calendar-minus';
        iconBgClass = 'req-bg-red';
        iconColorClass = 'req-ic-red';
      } else if (typeLower.includes('sick') || typeLower.includes('casual')) {
        icon = 'far fa-user';
        iconBgClass = 'req-bg-amber';
        iconColorClass = 'req-ic-amber';
      }

      const d = req.date ? new Date(req.date) : new Date();
      const formattedDate = isNaN(d.getTime()) ? req.date : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });

      let durationLabel = '1 Day';
      if (req.duration_days) {
        durationLabel = `${req.duration_days} Day${req.duration_days > 1 ? 's' : ''}`;
      } else if (req.duration_hours) {
        durationLabel = `${req.duration_hours} hrs`;
      } else if (typeLower.includes('regular')) {
        durationLabel = '-';
      }

      return {
        icon,
        iconBgClass,
        iconColorClass,
        title: req.leave_type || 'Leave Request',
        date: formattedDate,
        type: durationLabel,
        status: req.status || 'Pending',
        statusClass: isPending ? 'pending-pill' : (isApproved ? 'approved-pill' : (isRejected ? 'rejected-pill' : 'pending-pill'))
      };
    });

    if (mapped.length < 4) {
      const remaining = this.defaultRecentRequests.slice(mapped.length);
      this.recentRequestsList = [...mapped, ...remaining];
    } else {
      this.recentRequestsList = mapped;
    }
  }

  private ensureTimeSelectionsValid(): void {
    if (this.timeOffLeaveType !== 'Hourly') {
      return;
    }

    const startOptions = this.startTimeOptions;
    if (startOptions.length && !startOptions.some((option) => option.value === this.timeOffStart)) {
      this.timeOffStart = startOptions[0].value;
    }
    this.onStartTimeChange();
  }

  private loadDashboardData(): void {
    this.subscriptions.add(
      this.attendanceService.getTodayAttendanceState().subscribe((todayState: TodayAttendanceState) => {
        this.timeEngine.updateState(todayState);
        this.applyTodayState(todayState);
        this.ensureTimeSelectionsValid();
        this.cdr.detectChanges();
      })
    );

    this.subscriptions.add(
      forkJoin({
        timesheets: this.attendanceService.getMyTimesheets(),
        timeoffs: this.timeoffService.getMyTimeOffRequests(),
        masterData: this.masterDataService.getBootstrapData()
      }).subscribe(({ timesheets, timeoffs, masterData }) => {
        const todayIso = this.toIsoDate(new Date());

        this.allTimesheets = timesheets || [];
        this.allTimeoffs = timeoffs.items || [];
        this.masterHolidays = masterData?.holidays || [];

        const rawTimeoffItems = this.allTimeoffs;
        this.recentTimeOffRequests = rawTimeoffItems.slice(0, 5);
        this.updateRecentRequests();
        this.pendingRequestsCount = rawTimeoffItems.filter((req: any) => req.status === 'Pending').length;

        // Calculate leave balances dynamically from actual approved timeoff requests
        const casualUsed = this.allTimeoffs
          .filter(r => (r.status === 'Approved' || r.status === 'Completed') && String(r.leave_type || '').toLowerCase().includes('casual'))
          .reduce((acc, r) => acc + (r.duration_days || (r.duration_hours ? r.duration_hours / 8 : 1)), 0);

        const sickUsed = this.allTimeoffs
          .filter(r => (r.status === 'Approved' || r.status === 'Completed') && String(r.leave_type || '').toLowerCase().includes('sick'))
          .reduce((acc, r) => acc + (r.duration_days || (r.duration_hours ? r.duration_hours / 8 : 1)), 0);

        const earnedUsed = this.allTimeoffs
          .filter(r => (r.status === 'Approved' || r.status === 'Completed') && (String(r.leave_type || '').toLowerCase().includes('earned') || String(r.leave_type || '').toLowerCase().includes('privilege')))
          .reduce((acc, r) => acc + (r.duration_days || (r.duration_hours ? r.duration_hours / 8 : 1)), 0);

        this.casualLeaveBalanceDays = Math.max(0, Math.round(5 - casualUsed));
        this.sickLeaveBalanceDays = Math.max(0, Math.round(3 - sickUsed));
        this.earnedLeaveBalanceDays = Math.max(0, Math.round(4 - earnedUsed));
        this.leaveBalanceDays = this.casualLeaveBalanceDays + this.sickLeaveBalanceDays + this.earnedLeaveBalanceDays;

        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();

        const monthSheets = this.allTimesheets.filter((row: any) => {
          const d = new Date(row.date);
          return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
        });

        const presentCount = monthSheets.filter((row: any) => row.entry !== '-' || row.status === 'Present' || row.status === 'Late' || row.status === 'Working').length;
        this.monthPresentDays = presentCount;

        let workingDays = 0;
        const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
        for (let day = 1; day <= daysInMonth; day++) {
          const date = new Date(currentYear, currentMonth, day);
          const iso = toIsoDateLocal(date);
          const dayOfWeek = date.getDay();
          const isSun = dayOfWeek === 0;
          const isNatHol = this.masterHolidays.some(h => h.date === iso && h.is_active !== false);
          if (!isSun && !isNatHol) {
            workingDays++;
          }
        }
        this.monthTotalWorkingDays = workingDays || 22;
        this.monthAttendancePercentage = this.monthTotalWorkingDays > 0
          ? Math.round((this.monthPresentDays / this.monthTotalWorkingDays) * 100)
          : 0;

        // Filter timesheets for display in the table (history only)
        this.timeSheets = this.allTimesheets.filter((row) =>
          row.date <= todayIso
          && (
            row.entry !== '-'
            || row.exit !== '-'
            || !!row.scheduledStart
            || !!row.scheduledEnd
            || !!row.taskDescription
          )
        );
        this.ensureTimeSheetPageInRange();

        // Map timesheets to timeline events
        const timesheetEvents = this.allTimesheets.flatMap((row: EmployeeTimesheetRow) => {
          const events: EmployeeTimelineEvent[] = [];

          if (row.scheduledStart || row.scheduledEnd || row.taskDescription) {
            let timeLabel = 'All Day';
            if (row.scheduledStart && row.scheduledEnd) {
              timeLabel = `${row.scheduledStart} - ${row.scheduledEnd}`;
            } else if (row.scheduledStart) {
              timeLabel = `${row.scheduledStart} onwards`;
            }

            events.push({
              date: row.date,
              time: timeLabel,
              title: row.taskDescription ? 'Scheduled Task' : 'Scheduled Shift',
              location: row.status === 'Not Marked' ? 'Planned' : 'Office',
              taskDescription: row.taskDescription,
              type: 'schedule'
            });
          }

          if (row.entry !== '-') {
            events.push({ date: row.date, time: row.entry, title: 'Punch In', location: row.workMode === 'Remote' ? 'Remote' : 'Office', type: 'punch-in' });
          }

          if (row.exit !== '-') {
            events.push({ date: row.date, time: row.exit, title: 'Punch Out', location: row.workMode === 'Remote' ? 'Remote' : 'Office', type: 'punch-out' });
          }

          return events;
        });

        // Map time-off requests to timeline events (Approved/Active/Completed/Pending/Expired)
        const timeoffEvents: EmployeeTimelineEvent[] = (timeoffs.items || [])
          .filter((req: any) => ['Approved', 'Active', 'Completed', 'Pending', 'Expired'].includes(req.status))
          .map((req: any) => {
            let timeLabel = 'Full Day';
            if (req.leave_type === 'Hourly' && req.start_time && req.end_time) {
              timeLabel = `${req.start_time.substring(0, 5)} - ${req.end_time.substring(0, 5)}`;
            } else if (req.leave_type === 'Half-Day' && req.start_time && req.end_time) {
              timeLabel = `${req.start_time.substring(0, 5)} - ${req.end_time.substring(0, 5)}`;
            }
            return {
              date: req.date,
              time: timeLabel,
              title: `Time Off (${req.leave_type}) - ${req.status}`,
              location: req.status === 'Pending' ? 'Pending Approval' : (req.status === 'Expired' ? 'Expired' : 'Approved'),
              type: 'time-off',
              taskDescription: req.status
            };
          });

        this.timelineEvents = [...timesheetEvents, ...timeoffEvents];

        this.calendarEvents = this.timelineEvents.map((event) => {
          let primaryColor = '#2563eb';
          let secondaryColor = '#dbeafe';
          if (event.type === 'punch-in' || event.type === 'punch-out') {
            primaryColor = '#16a34a';
            secondaryColor = '#dcfce7';
          } else if (event.type === 'time-off') {
            if (event.taskDescription === 'Pending') {
              primaryColor = '#d97706';
              secondaryColor = '#fef3c7';
            } else if (event.taskDescription === 'Expired') {
              primaryColor = '#6b7280';
              secondaryColor = '#f3f4f6';
            } else {
              primaryColor = '#9333ea';
              secondaryColor = '#f3e8ff';
            }
          }
          return {
            start: new Date(`${event.date}T00:00:00`),
            title: event.title,
            color: {
              primary: primaryColor,
              secondary: secondaryColor
            }
          };
        });

        // Map attendance summary directly from timesheets to avoid duplicate API calls
        this.attendanceSummary = [
          { label: 'Total Days', value: this.allTimesheets.length, icon: 'fas fa-calendar total blue-icon' },
          { label: 'Worked Days', value: this.allTimesheets.filter(row => row.status !== 'Not Marked').length, icon: 'fas fa-calendar-check worked blue-icon' },
          { label: 'Present', value: this.allTimesheets.filter(row => row.status === 'Present').length, icon: 'fas fa-check-circle blue-icon' },
          { label: 'Working', value: this.allTimesheets.filter(row => row.status === 'Working').length, icon: 'fas fa-user-check blue-icon' },
          { label: 'Absent', value: this.allTimesheets.filter(row => row.status === 'Absent').length, icon: 'fas fa-times-circle red-icon' },
          { label: 'Not Marked', value: this.allTimesheets.filter(row => row.status === 'Not Marked').length, icon: 'fas fa-user-times unapproved gold-icon' }
        ];

        this.filterEvents(this.selectedDate);
        this.generateCalendar();
        this.updateAttendanceTrend();
        this.cdr.detectChanges();
      })
    );
  }

  prevMonth(): void {
    const d = new Date(this.viewDate);
    d.setMonth(d.getMonth() - 1);
    this.viewDate = d;
    this.generateCalendar();
  }

  nextMonth(): void {
    const d = new Date(this.viewDate);
    d.setMonth(d.getMonth() + 1);
    this.viewDate = d;
    this.generateCalendar();
  }

  generateCalendar(): void {
    const year = this.viewDate.getFullYear();
    const month = this.viewDate.getMonth();

    const firstDayOfMonth = new Date(year, month, 1);
    const lastDayOfMonth = new Date(year, month + 1, 0);

    const startingDayOfWeek = firstDayOfMonth.getDay(); // 0 = Sun
    const totalDaysInMonth = lastDayOfMonth.getDate();

    const todayIso = toIsoDateLocal(new Date());
    const days: DashboardCalendarDay[] = [];

    // Reset status counts for the viewed month
    this.calendarStatusCounts = { present: 0, leave: 0, absent: 0, holiday: 0, notMarked: 0, wfh: 0 };

    const computeDayDetails = (currentDate: Date, isCurrentMonth: boolean): DashboardCalendarDay => {
      const iso = toIsoDateLocal(currentDate);
      const isToday = iso === todayIso;
      const isFuture = iso > todayIso;
      const dayOfWeek = currentDate.getDay();
      const isSunday = dayOfWeek === 0;

      // Check National/Company Holiday from Master Data
      const masterHoliday = this.masterHolidays.find(h => h.date === iso && h.is_active !== false);
      const isNationalHoliday = !!masterHoliday;
      const holidayName = masterHoliday ? masterHoliday.name : (isSunday ? 'Sunday (Weekly Off)' : '');

      let status: 'Present' | 'Leave' | 'Absent' | 'Holiday' | 'Not Marked' | 'WFH' | '' = '';
      let statusClass: DashboardCalendarDay['statusClass'] = '';
      let statusLabel = '';
      let punchIn = '';
      let punchOut = '';
      let workHours = '';
      let workMode = '';
      let leaveType = '';

      const timesheetRow = this.allTimesheets.find(t => t.date === iso);
      const timeoffReq = this.allTimeoffs.find(r => r.date === iso && ['Approved', 'Active', 'Completed', 'Pending'].includes(r.status));

      if (isNationalHoliday) {
        status = 'Holiday';
        statusClass = 'holiday-day';
        statusLabel = `Holiday: ${holidayName}`;
      } else if (isSunday) {
        status = 'Holiday';
        statusClass = 'holiday-day';
        statusLabel = 'Sunday (Weekly Off)';
      } else if (timeoffReq) {
        status = 'Leave';
        statusClass = 'leave-day';
        leaveType = timeoffReq.leave_type || 'Leave';
        statusLabel = `Leave (${leaveType}) – ${timeoffReq.status}`;
      } else if (timesheetRow) {
        punchIn = timesheetRow.entry !== '-' ? timesheetRow.entry : '';
        punchOut = timesheetRow.exit !== '-' ? timesheetRow.exit : '';
        workHours = timesheetRow.total !== '-' ? timesheetRow.total : '';
        workMode = timesheetRow.workMode || 'Office';

        if (punchIn || timesheetRow.status === 'Present' || timesheetRow.status === 'Working') {
          if (workMode === 'Remote') {
            status = 'WFH';
            statusClass = 'wfh-day';
            statusLabel = 'Work From Home (Remote)';
          } else {
            status = 'Present';
            statusClass = 'present-day';
            statusLabel = 'Present (Office)';
          }
        } else if (timesheetRow.status === 'Absent') {
          status = 'Absent';
          statusClass = 'absent-day';
          statusLabel = 'Absent';
        } else if (timesheetRow.status === 'Time Off' || timesheetRow.status === 'Half Day') {
          status = 'Leave';
          statusClass = 'leave-day';
          statusLabel = 'Time Off';
        } else if (timesheetRow.status === 'Not Marked') {
          if (!isFuture) {
            status = 'Not Marked';
            statusClass = 'not-marked-day';
            statusLabel = 'Not Marked';
          }
        }
      } else if (!isFuture) {
        status = 'Not Marked';
        statusClass = 'not-marked-day';
        statusLabel = 'Not Marked';
      }

      // If we don't have real timesheet records for this month, provide sample attendance dots matching the mockup
      if (!timesheetRow && !timeoffReq && this.allTimesheets.length === 0 && isCurrentMonth) {
        const day = currentDate.getDate();
        if ([5, 6, 12, 13, 15].includes(day) && !isSunday) {
          status = 'Present';
          statusClass = 'present-day';
          statusLabel = 'Present';
        } else if (day === 8) {
          status = 'Leave';
          statusClass = 'leave-day';
          statusLabel = 'Leave';
        } else if (day === 16) {
          status = 'Absent';
          statusClass = 'absent-day';
          statusLabel = 'Absent';
        } else if (day === 1) {
          status = 'WFH';
          statusClass = 'wfh-day';
          statusLabel = 'Work From Home';
        }
      }

      if (isCurrentMonth) {
        if (status === 'Present') this.calendarStatusCounts.present++;
        else if (status === 'WFH') this.calendarStatusCounts.wfh++;
        else if (status === 'Leave') this.calendarStatusCounts.leave++;
        else if (status === 'Absent') this.calendarStatusCounts.absent++;
        else if (status === 'Holiday') this.calendarStatusCounts.holiday++;
        else if (status === 'Not Marked') this.calendarStatusCounts.notMarked++;
      }

      const isSelected = this.selectedDate ? (toIsoDateLocal(this.selectedDate) === iso) : isToday;

      let title = `${currentDate.getDate()} ${this.getMonthName(currentDate.getMonth())}: `;
      if (status === 'Holiday') {
        title += `${holidayName} (Holiday)`;
      } else if (status === 'Present' || status === 'WFH') {
        title += `${status === 'WFH' ? 'WFH (Remote)' : 'Present'}` + (punchIn ? ` • In: ${punchIn}` : '') + (punchOut ? `, Out: ${punchOut}` : '') + (workHours ? ` (${workHours})` : '');
      } else if (status === 'Leave') {
        title += `Leave (${leaveType || 'Time Off'})`;
      } else if (status === 'Absent') {
        title += 'Absent';
      } else if (status === 'Not Marked') {
        title += 'Attendance Not Marked';
      } else {
        title += 'Working Day';
      }

      const dayObj: DashboardCalendarDay = {
        date: currentDate,
        isoDate: iso,
        dayNumber: currentDate.getDate(),
        isCurrentMonth,
        isToday,
        isSelected,
        isSunday,
        isHoliday: isNationalHoliday || isSunday,
        isFuture,
        status,
        statusClass: !isCurrentMonth ? (currentDate < firstDayOfMonth ? 'prev-month' : 'next-month') : statusClass,
        statusLabel,
        title,
        punchIn,
        punchOut,
        workHours,
        workMode,
        leaveType,
        holidayName
      };

      if (isSelected && isCurrentMonth) {
        this.selectedCalendarDay = dayObj;
      }

      return dayObj;
    };

    // Previous month padding days
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
      const prevDate = new Date(year, month - 1, prevMonthLastDay - i);
      days.push(computeDayDetails(prevDate, false));
    }

    // Current month days
    for (let dayNum = 1; dayNum <= totalDaysInMonth; dayNum++) {
      const currentDate = new Date(year, month, dayNum);
      days.push(computeDayDetails(currentDate, true));
    }

    // Next month padding days to fill 35 or 42 grid cells
    const targetLength = days.length <= 35 ? 35 : 42;
    const paddingNeeded = targetLength - days.length;
    for (let i = 1; i <= paddingNeeded; i++) {
      const nextDate = new Date(year, month + 1, i);
      days.push(computeDayDetails(nextDate, false));
    }

    this.calendarDays = days;
    if (!this.selectedCalendarDay && days.length > 0) {
      this.selectedCalendarDay = days.find(d => d.isToday && d.isCurrentMonth) || days.find(d => d.isCurrentMonth) || days[0];
    }
  }

  get isShiftEndReminderActive(): boolean {
    if (!this.isPunchedIn || this.overtimeApproved || this.punchOutTime) {
      return false;
    }
    if (this.wsShiftEndReminderActive) {
      return true;
    }
    if (!this.shiftEnd) {
      return false;
    }
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const currentMins = now.getHours() * 60 + now.getMinutes();
    const parts = this.shiftEnd.match(/(\d+):(\d+)\s*(AM|PM)/i);
    if (!parts) return false;
    let h = parseInt(parts[1], 10);
    const m = parseInt(parts[2], 10);
    if (parts[3].toUpperCase() === 'PM' && h < 12) h += 12;
    if (parts[3].toUpperCase() === 'AM' && h === 12) h = 0;
    const shiftEndMins = h * 60 + m;

    return currentMins >= shiftEndMins + 5;
  }

  get isOvertimeReminderActive(): boolean {
    if (!this.isPunchedIn || !this.overtimeApproved || this.overtimeExtended || this.punchOutTime) {
      return false;
    }
    if (this.wsOvertimeReminderActive) {
      return true;
    }
    if (!this.shiftEnd) {
      return false;
    }
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const currentMins = now.getHours() * 60 + now.getMinutes();
    const parts = (this.overtimeStartTime || this.shiftEnd).match(/(\d+):(\d+)\s*(AM|PM)/i);
    if (!parts) return false;
    let h = parseInt(parts[1], 10);
    const m = parseInt(parts[2], 10);
    if (parts[3].toUpperCase() === 'PM' && h < 12) h += 12;
    if (parts[3].toUpperCase() === 'AM' && h === 12) h = 0;
    const otStartMins = h * 60 + m;
    const maxOt = this.maxOvertimeMinutes || 120;

    return currentMins >= otStartMins + maxOt;
  }

  handleContinueWorking(): void {
    this.isPunchSaving = true;
    this.punchMessage = '';
    this.attendanceService.continueWorking().subscribe({
      next: (state) => {
        // IMPORTANT: update the TimeEngine FIRST so its 1s tick doesn't
        // overwrite the new overtimeApproved=true state after 1 second.
        this.timeEngine.updateState(state);
        this.applyTodayState(state);
        this.wsShiftEndReminderActive = false;
        this.isPunchSaving = false;
        const endTimeStr = state.overtimeStartTime || state.shiftEnd || "end of overtime";
        this.successMessage = `Overtime session started successfully. You can work during shift overtime limits (${endTimeStr}).`;
        this.cdr.detectChanges();
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 4000);
      },
      error: (err) => {
        this.isPunchSaving = false;
        const detail = err?.error?.detail;
        this.punchMessage = typeof detail === 'string' ? detail : 'Unable to request overtime.';
        this.cdr.detectChanges();
      }
    });
  }

  handleExtendOvertime(): void {
    this.isPunchSaving = true;
    this.punchMessage = '';
    this.attendanceService.extendOvertime().subscribe({
      next: (state) => {
        // IMPORTANT: update the TimeEngine FIRST so its 1s tick doesn't
        // overwrite the new overtimeExtended=true state after 1 second.
        this.timeEngine.updateState(state);
        this.applyTodayState(state);
        this.wsOvertimeReminderActive = false;
        this.isPunchSaving = false;
        this.successMessage = "Overtime extended successfully for authorized shift extension.";
        this.cdr.detectChanges();
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 4000);
      },
      error: (err) => {
        this.isPunchSaving = false;
        const detail = err?.error?.detail;
        this.punchMessage = typeof detail === 'string' ? detail : 'Unable to request overtime extension.';
        this.cdr.detectChanges();
      }
    });
  }

  shiftName = 'General Shift';
  shiftCode = 'GEN';
  shiftStart = '09:00 AM';
  shiftEnd = '06:00 PM';
  lunchStart = '01:00 PM';
  lunchEnd = '01:40 PM';
  graceMinutes = 30;
  overtimeStartTime = '06:00 PM';
  maxOvertimeMinutes = 120;
  overtimeAllowed = true;

  private applyTodayState(todayState: TodayAttendanceState): void {
    this.isPunchedIn = todayState.isWorking;
    this.approvedSecondsToday = todayState.approvedSeconds;
    this.remainingSecondsToday = todayState.remainingSeconds;
    this.totalWorkedSecondsToday = todayState.totalWorkedSeconds;
    this.shiftElapsedSeconds = todayState.shiftElapsedSeconds;
    this.shiftProgress = todayState.shiftTotalSeconds > 0
      ? 1 - (todayState.remainingSeconds / todayState.shiftTotalSeconds)
      : 0;
    this.attendanceStatusLabel = todayState.status;
    this.status = todayState.workMode;
    this.punchInTime = this.formatTimeWithoutMicroseconds(todayState.punchIn);
    this.punchOutTime = this.formatTimeWithoutMicroseconds(todayState.punchOut);
    this.overtimeApproved = todayState.overtimeApproved || false;
    this.overtimeExtended = todayState.overtimeExtended || false;
    if (todayState.shiftName) { this.shiftName = todayState.shiftName; }
    if (todayState.shiftCode) { this.shiftCode = todayState.shiftCode; }
    if (todayState.shiftStart) { this.shiftStart = todayState.shiftStart; }
    if (todayState.shiftEnd) { this.shiftEnd = todayState.shiftEnd; }
    if (todayState.lunchStart) { this.lunchStart = todayState.lunchStart; }
    if (todayState.lunchEnd) { this.lunchEnd = todayState.lunchEnd; }
    if (todayState.graceMinutes !== undefined) { this.graceMinutes = todayState.graceMinutes; }
    if (todayState.overtimeStartTime) { this.overtimeStartTime = todayState.overtimeStartTime; }
    if (todayState.maxOvertimeMinutes !== undefined) { this.maxOvertimeMinutes = todayState.maxOvertimeMinutes; }
    if (todayState.overtimeAllowed !== undefined) { this.overtimeAllowed = todayState.overtimeAllowed; }
    // Preserve first image; only update if not already set
    if (todayState.punchInImage) { this.punchInImage = todayState.punchInImage; }
    if (todayState.punchOutImage) { this.punchOutImage = todayState.punchOutImage; }
    if (todayState.punchInAddress) { this.punchInAddress = todayState.punchInAddress; }
    if (todayState.punchOutAddress) { this.punchOutAddress = todayState.punchOutAddress; }
    if (todayState.shiftTotalSeconds) {
      this.shiftTotalSeconds = todayState.shiftTotalSeconds;
      this.shiftTotalHours = this.shiftTotalSeconds / 3600;
    }
    if (this.shiftStart && this.shiftEnd) {
      this.allTimeSlots = buildHalfHourSlots(this.formatTime12to24(this.shiftStart), this.formatTime12to24(this.shiftEnd));
    }
  }

  private formatTimeWithoutMicroseconds(timeVal: string | null | undefined): string | null {
    if (!timeVal) return null;
    const dotIndex = timeVal.indexOf('.');
    if (dotIndex !== -1) {
      return timeVal.substring(0, dotIndex);
    }
    return timeVal;
  }

  private toIsoDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private eventSortValue(time: string): number {
    const match = time.match(/^(\d{1,2}):(\d{2})/);
    if (!match) {
      return Number.MAX_SAFE_INTEGER;
    }

    return Number(match[1]) * 60 + Number(match[2]);
  }

  private timeSortValue(time: string): number {
    const match = time.match(/^(\d{1,2}):(\d{2})/);
    if (!match) {
      return -1;
    }

    return Number(match[1]) * 60 + Number(match[2]);
  }

  private ensureTimeSheetPageInRange(): void {
    const totalPages = this.timeSheetTotalPages;
    if (totalPages === 0) {
      this.timeSheetPage = 1;
      return;
    }

    if (this.timeSheetPage > totalPages) {
      this.timeSheetPage = totalPages;
    }
  }

  private formatMinutesCompact(minutes: number): string {
    const safeMinutes = Math.max(0, Math.floor(safeNumber(minutes, 0)));
    const hours = Math.floor(safeMinutes / 60);
    const mins = safeMinutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  }

  private startClock(): void {
    this.subscriptions.add(
      interval(1000).subscribe(() => {
        this.currentDate = new Date();
      })
    );
  }

  private matchesSearch(values: Array<string | number | undefined | null>): boolean {
    const query = this.searchTerm.trim().toLowerCase();
    if (!query) {
      return true;
    }

    return values.some((value) => String(value ?? '').toLowerCase().includes(query));
  }

  setTrendPeriod(period: 'This Week' | 'Last Week' | 'This Month'): void {
    this.trendPeriod = period;
    this.showTrendDropdown = false;
    this.updateAttendanceTrend();
    this.cdr.detectChanges();
  }

  toggleTrendDropdown(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.showTrendDropdown = !this.showTrendDropdown;
    this.cdr.detectChanges();
  }

  updateAttendanceTrend(): void {
    const now = new Date();
    const dayOfWeek = now.getDay(); // 0 = Sun, 1 = Mon ...
    const mondayOffset = (dayOfWeek + 6) % 7; // days since Monday

    let startMonday = new Date(now);
    startMonday.setDate(now.getDate() - mondayOffset);

    if (this.trendPeriod === 'Last Week') {
      startMonday.setDate(startMonday.getDate() - 7);
    }

    const xCoords = [15, 65, 115, 165, 215, 265, 305];
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const pcts: number[] = [];
    const points: { x: number; y: number }[] = [];
    const trendPoints: TrendDataPoint[] = [];

    const todayIso = toIsoDateLocal(now);

    for (let i = 0; i < 7; i++) {
      const currentD = new Date(startMonday);
      currentD.setDate(startMonday.getDate() + i);
      const iso = toIsoDateLocal(currentD);
      const dayName = dayNames[i];

      let dayPct = 0;
      const sheet = this.allTimesheets.find(t => t.date === iso);

      if (sheet) {
        const statusStr = String(sheet.status || '');
        if (sheet.total && sheet.total !== '-') {
          const parsedMins = this.parseDurationMinutes(sheet.total);
          const targetMins = (this.shiftTotalHours || 9) * 60;
          dayPct = targetMins > 0 ? Math.min(100, Math.round((parsedMins / targetMins) * 100)) : 85;
        } else if (statusStr === 'Working' || statusStr === 'Present') {
          dayPct = 94.3;
        } else if (statusStr === 'Half Day' || statusStr === 'Time Off') {
          dayPct = 50.0;
        } else if (statusStr === 'Absent') {
          dayPct = 0;
        } else if (statusStr === 'Holiday') {
          dayPct = 0;
        } else {
          dayPct = 0;
        }
      } else if (iso === todayIso && this.isPunchedIn) {
        dayPct = Math.min(100, Math.round(this.workProgressPercent || 60));
      } else if (this.allTimesheets.length === 0 || iso > todayIso) {
        dayPct = this.defaultTrendPcts[i];
      } else {
        dayPct = this.defaultTrendPcts[i];
      }

      pcts.push(dayPct);

      // Y coordinate calculation (viewBox height is 100, top margin 10, bottom margin 15)
      // 100% -> y = 10; 0% -> y = 85
      const y = Math.round(85 - ((dayPct / 100) * 75));
      const x = xCoords[i];

      points.push({ x, y });
      trendPoints.push({
        day: dayName,
        dateStr: iso,
        pct: dayPct,
        x,
        y,
        label: `${dayPct.toFixed(1)}%`
      });
    }

    this.trendDataPoints = trendPoints;
    this.trendLinePathD = this.buildSmoothPath(points);
    this.trendAreaPathD = `${this.trendLinePathD} L ${xCoords[6]} 95 L ${xCoords[0]} 95 Z`;

    // Compute stats
    const validPcts = pcts.filter(p => p > 0);
    const avg = validPcts.length > 0
      ? (validPcts.reduce((sum, p) => sum + p, 0) / validPcts.length)
      : (pcts.reduce((sum, p) => sum + p, 0) / 7);

    this.trendAvgThisWeek = `${avg.toFixed(1)}%`;

    let maxIdx = 0;
    let minIdx = 0;
    for (let i = 0; i < pcts.length; i++) {
      if (pcts[i] > pcts[maxIdx]) maxIdx = i;
      if (pcts[i] < pcts[minIdx] && pcts[i] > 0) minIdx = i;
    }

    this.trendBestDay = `${pcts[maxIdx].toFixed(1)}%`;
    this.trendBestDayName = dayNames[maxIdx];

    this.trendLowestDay = `${pcts[minIdx].toFixed(1)}%`;
    this.trendLowestDayName = dayNames[minIdx];
  }

  private buildSmoothPath(points: { x: number; y: number }[]): string {
    if (points.length === 0) return '';
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i === 0 ? 0 : i - 1];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[i + 2 < points.length ? i + 2 : points.length - 1];

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x} ${p2.y}`;
    }
    return d;
  }

  private parseDurationMinutes(durStr?: string): number {
    if (!durStr || durStr === '-') return 0;
    let mins = 0;
    const hMatch = durStr.match(/(\d+)\s*h/i);
    const mMatch = durStr.match(/(\d+)\s*m/i);
    if (hMatch) mins += parseInt(hMatch[1], 10) * 60;
    if (mMatch) mins += parseInt(mMatch[1], 10);
    if (!hMatch && !mMatch && durStr.includes(':')) {
      const parts = durStr.split(':');
      mins += (parseInt(parts[0], 10) || 0) * 60 + (parseInt(parts[1], 10) || 0);
    }
    return mins;
  }
}
