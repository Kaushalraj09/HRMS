import { CommonModule } from '@angular/common';
// Trigger dev server recompilation of dashboard component after modal import fix

import { ChangeDetectorRef, Component, Injectable, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CalendarModule, CalendarDateFormatter, CalendarNativeDateFormatter, DateFormatterParams } from 'angular-calendar';
import { CalendarEvent } from 'calendar-utils';
import { finalize, Subscription, interval, forkJoin, of, catchError } from 'rxjs';

import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { RegularizationService } from '../../../../core/services/regularization.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TimeEngineService } from '../../../../core/services/time-engine.service';
import { MasterDataService } from '../../../../core/services/master-data.service';
import { DocumentService } from '../../../../core/services/document.service';
import { MyProfileService } from '../../../../core/services/profile.service';
import { Holiday, WorkLocation } from '../../../../core/models/master-data.model';
import { RegularizationRequestItem } from '../../../../core/models/regularization.model';
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
import { FooterComponent } from '../../../../shared/components/footer/footer';

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

export interface LeaveBalanceItem {
  id?: number;
  name: string;
  code: string;
  initial: string;
  days: number;
  colorClass: string;
  textClass: string;
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

export interface DashboardScheduleDisplayItem {
  time: string;
  title: string;
  sub?: string;
  span?: string;
  dotColor: 'blue' | 'orange' | 'purple' | 'green' | 'red';
  lineType: 'down' | 'both' | 'up' | 'none';
}

export interface TrendDataPoint {
  day: string;
  dateStr: string;
  pct: number;
  x: number;
  y: number;
  label: string;
  status?: string;
  duration?: string;
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
    EmpSidebar,
    FooterComponent
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
  overtimeSecondsToday = 0;

  shiftTotalHours = 9;
  shiftTotalSeconds = 9 * 3600;
  allTimeSlots: TimeSlotOption[] = [];

  recentTimeOffRequests: any[] = [];
  recentRequestsList: DashboardRecentRequestItem[] = [];

  pendingRequestsCount = 0;
  monthPresentDays = 0;
  monthTotalWorkingDays = 22;
  monthAttendancePercentage = 0;
  casualLeaveBalanceDays = 3;
  sickLeaveBalanceDays = 5;
  earnedLeaveBalanceDays = 10;
  leaveBalanceDays = 18;

  leaveBalanceItems: LeaveBalanceItem[] = [
    { name: 'Casual Leave', code: 'CL', initial: 'C', days: 3, colorClass: 'blue-icon', textClass: 'blue-days' },
    { name: 'Sick Leave', code: 'SL', initial: 'S', days: 5, colorClass: 'green-icon', textClass: 'green-days' },
    { name: 'Earned Leave', code: 'EL', initial: 'E', days: 10, colorClass: 'orange-icon', textClass: 'orange-days' },
    { name: 'Comp Off', code: 'CO', initial: 'C', days: 2, colorClass: 'amber-icon', textClass: 'amber-days' },
    { name: 'Half Day', code: 'HD', initial: 'H', days: 3, colorClass: 'purple-icon', textClass: 'purple-days' },
  ];

  get totalAvailableLeaveDays(): number {
    if (this.leaveBalanceItems && this.leaveBalanceItems.length > 0) {
      return Math.round(this.leaveBalanceItems.reduce((acc, item) => acc + (Number(item.days) || 0), 0));
    }
    return Math.round(this.casualLeaveBalanceDays + this.sickLeaveBalanceDays + this.earnedLeaveBalanceDays);
  }

  formatTwoDigits(num: number): string {
    const intVal = Math.round(Number(num) || 0);
    return intVal < 10 ? `0${intVal}` : `${intVal}`;
  }

  get isTodayWorkingDay(): boolean {
    const todayIso = toIsoDateLocal(new Date());
    const isSunday = new Date().getDay() === 0;
    const isHoliday = this.masterHolidays.some(h => h.date === todayIso && h.is_active !== false);
    return !isSunday && !isHoliday;
  }

  timeOffDate = toIsoDateLocal(new Date());
  timeOffLeaveType: 'Half Day' | 'Full Day' = 'Half Day';
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
  allRegularizations: RegularizationRequestItem[] = [];
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
  hoveredTrendPoint: TrendDataPoint | null = null;
  hoveredTrendIndex: number | null = null;

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
  public isFaceDetected = false;
  private faceDetectInterval: any = null;
  public pendingPunchWorkMode: WorkMode = 'Office';
  public pendingPunchLatitude: number | undefined;
  public pendingPunchLongitude: number | undefined;
  public pendingPunchAddress: string | undefined;
  public isLocationLoading = false;
  public masterWorkLocations: WorkLocation[] = [];
  public assignedWorkLocationName = '';

  get isAssignedRemoteWorker(): boolean {
    const loc = (this.assignedWorkLocationName || '').trim().toLowerCase();
    if (loc === 'remote' || loc.includes('remote') || loc === 'wfh') {
      return true;
    }
    const matched = this.masterWorkLocations.find(
      (l) => (l.name || '').trim().toLowerCase() === loc || (l.code || '').trim().toLowerCase() === loc
    );
    return (matched?.location_type || '').toLowerCase() === 'remote';
  }

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

  docSummary: any = {
    total_required: 0,
    total_optional: 0,
    uploaded: 0,
    pending_review: 0,
    verified: 0,
    rejected: 0,
    missing: 0,
    completion_percentage: 0
  };
  dashboardDocList: any[] = [];

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly empsidebarService: EmpSidebarService,
    private readonly router: Router,
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly authService: AuthService,
    private readonly timeEngine: TimeEngineService,
    private readonly masterDataService: MasterDataService,
    private readonly documentService: DocumentService,
    private readonly myProfileService: MyProfileService,
    private readonly regularizationService: RegularizationService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isEmpSidebarOpen$ = this.empsidebarService.isEmpSidebarOpen$;
    const checkIsHome = (url: string) => {
      const clean = (url || '').split('?')[0].split('#')[0].replace(/\/+$/, '');
      return clean === '/emp-dashboard' || clean === '';
    };
    this.isDashboardHome = checkIsHome(this.router.url);
    this.userName = this.authService.getDisplayName();

    this.subscriptions.add(
      this.router.events.subscribe((event) => {
        if (event instanceof NavigationEnd) {
          this.isDashboardHome = checkIsHome(event.urlAfterRedirects || event.url);
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

    this.loadMyDocumentsSummary();
    this.subscriptions.add(
      this.documentService.documentUpdated$.subscribe(() => {
        this.loadMyDocumentsSummary();
      })
    );

    this.initialize();
    this.startClock();
    this.updateAttendanceTrend();
  }

  loadMyDocumentsSummary(): void {
    this.documentService.getMyDocuments().subscribe({
      next: (res) => {
        if (res && res.summary) {
          this.docSummary = res.summary;
          this.dashboardDocList = res.documents || [];
          this.cdr.markForCheck();
        }
      },
      error: () => {}
    });
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

  get formattedAttendanceStatus(): string {
    if (this.attendanceStatusLabel === 'EARLY_PENDING_APPROVAL') {
      return 'Early Pending Approval';
    }
    if (this.attendanceStatusLabel === 'WITHIN_GRACE') {
      return 'Working (Grace)';
    }
    if (this.attendanceStatusLabel === 'LATE') {
      return 'Working (Late)';
    }
    if (this.overtimeApproved && this.isPunchedIn) {
      return 'Working (OT)';
    }
    return this.attendanceStatusLabel || (this.isPunchedIn ? 'Working' : 'Not Marked');
  }

  get todayAttendancePillLabel(): string {
    if (this.isPunchedIn) {
      if (this.overtimeApproved) {
        return 'Overtime';
      }
      return 'Working';
    }
    if (this.punchOutTime || this.attendanceStatusLabel === 'Present' || this.punchInTime) {
      return 'Present';
    }
    if (this.attendanceStatusLabel && this.attendanceStatusLabel !== 'Not working' && this.attendanceStatusLabel !== 'Not Marked') {
      return this.formattedAttendanceStatus;
    }
    return 'Not Marked';
  }

  get todayAttendancePillClass(): string {
    if (this.isPunchedIn) {
      if (this.overtimeApproved) {
        return 'orange-pill';
      }
      return 'green-pill';
    }
    if (this.punchOutTime || this.attendanceStatusLabel === 'Present' || this.punchInTime) {
      return 'green-pill';
    }
    return 'gray-pill';
  }

  get todayPunchInDisplay(): string {
    if (!this.punchInTime) {
      return 'Not Marked';
    }
    return this.formatTime12h(this.punchInTime);
  }

  get maxOvertimeDisplay(): string {
    const mins = this.maxOvertimeMinutes || 120;
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return remMins > 0 ? `${hrs}h ${remMins}m` : `${hrs} hours`;
  }

  get overtimeDurationDisplay(): string {
    const otSecs = this.overtimeSecondsToday > 0 
      ? this.overtimeSecondsToday 
      : Math.max(0, this.totalWorkedSecondsToday - this.shiftTotalSeconds);
    if (otSecs <= 0 && !this.overtimeApproved) {
      return '';
    }
    const hrs = Math.floor(otSecs / 3600);
    const mins = Math.floor((otSecs % 3600) / 60);
    return `+${this.formatTwoDigits(hrs)}h ${this.formatTwoDigits(mins)}m`;
  }

  get shiftElapsedOrTargetDisplay(): string {
    if (this.overtimeApproved) {
      return this.targetWorkHoursDisplay;
    }
    return this.shiftElapsedDisplay;
  }

  get targetWorkHoursDisplay(): string {
    const totalSecs = this.shiftTotalSeconds || (this.shiftTotalHours ? this.shiftTotalHours * 3600 : 28800);
    const hours = Math.floor(totalSecs / 3600);
    const mins = Math.round((totalSecs % 3600) / 60);
    return `${this.formatTwoDigits(hours)}h ${this.formatTwoDigits(mins)}m`;
  }

  get displayOfficeLocation(): string {
    return (
      this.assignedWorkLocationName ||
      this.punchInAddress ||
      (this.masterWorkLocations && this.masterWorkLocations.length > 0 ? this.masterWorkLocations[0].name : '') ||
      'Office Location'
    );
  }

  get selectedDayScheduleItems(): DashboardScheduleDisplayItem[] {
    const selectedIso = this.selectedDate ? toIsoDateLocal(this.selectedDate) : toIsoDateLocal(new Date());
    const day = this.calendarDays.find(d => d.isoDate === selectedIso) || this.selectedCalendarDay;
    const isToday = selectedIso === toIsoDateLocal(new Date());

    const items: DashboardScheduleDisplayItem[] = [];

    // 1. Holiday / Weekly Off check
    if (day?.status === 'Holiday' || day?.isSunday || day?.isHoliday) {
      items.push({
        time: 'All Day',
        title: day?.holidayName || (day?.isSunday ? 'Sunday (Weekly Off)' : 'Company Holiday'),
        sub: 'No scheduled work hours today',
        span: 'Full Day Off',
        dotColor: 'purple',
        lineType: 'none'
      });
      return items;
    }

    // 2. Approved Leave check
    if (day?.status === 'Leave' && (!day.punchIn && !day.punchOut)) {
      items.push({
        time: 'All Day',
        title: day.statusLabel || `Leave (${day.leaveType || 'Approved'})`,
        sub: 'On Approved Leave',
        span: 'Full Day',
        dotColor: 'orange',
        lineType: 'none'
      });
      return items;
    }

    // 3. Working Day Shift Schedule & Actual Events
    const shiftStart = this.shiftStart || '09:00 AM';
    const shiftEnd = this.shiftEnd || '06:00 PM';
    const lunchStart = this.lunchStart || '01:00 PM';
    const lunchEnd = this.lunchEnd || '01:40 PM';
    const shiftName = this.shiftName || 'General Shift';
    const workMode = isToday ? (this.status || 'Office') : (day?.workMode || 'Office');

    interface RawScheduleEvent {
      minutes: number;
      item: DashboardScheduleDisplayItem;
    }

    const eventList: RawScheduleEvent[] = [];

    // A. Shift Starts
    const shiftStartMins = parseTimeToMinutes(this.formatTime12to24(shiftStart) || '09:00') ?? 540;
    eventList.push({
      minutes: shiftStartMins,
      item: {
        time: shiftStart,
        title: 'Shift Starts',
        sub: `${shiftName} (${workMode})`,
        span: 'Scheduled Start',
        dotColor: 'blue',
        lineType: 'down'
      }
    });

    // B. Punch In (Actual or Pending)
    const effectivePunchIn = isToday ? this.punchInTime : day?.punchIn;
    if (effectivePunchIn) {
      const punchInDisplay = this.formatTime12h(effectivePunchIn);
      const punchInMins = parseTimeToMinutes(this.formatTime12to24(effectivePunchIn) || '') ?? (shiftStartMins + 5);
      eventList.push({
        minutes: punchInMins,
        item: {
          time: punchInDisplay,
          title: 'Punch In',
          sub: isToday ? (this.isPunchedIn ? 'Currently Working' : 'Completed') : 'Punched In',
          span: `In: ${punchInDisplay}`,
          dotColor: 'green',
          lineType: 'both'
        }
      });
    } else if (isToday) {
      // Pending Punch In
      eventList.push({
        minutes: shiftStartMins + 1,
        item: {
          time: '--:--',
          title: 'Punch In (Pending)',
          sub: 'Not yet punched in today',
          span: 'Pending',
          dotColor: 'orange',
          lineType: 'both'
        }
      });
    }

    // C. Lunch Break Start & End
    const lunchStartMins = parseTimeToMinutes(this.formatTime12to24(lunchStart) || '13:00') ?? 780;
    const lunchEndMins = parseTimeToMinutes(this.formatTime12to24(lunchEnd) || '13:40') ?? 820;
    eventList.push({
      minutes: lunchStartMins,
      item: {
        time: lunchStart,
        title: 'Lunch Break',
        sub: 'Break Starts',
        span: `${lunchStart} - ${lunchEnd}`,
        dotColor: 'orange',
        lineType: 'both'
      }
    });
    eventList.push({
      minutes: lunchEndMins,
      item: {
        time: lunchEnd,
        title: 'Lunch Break End',
        sub: 'Shift Resumes',
        span: 'Resumed',
        dotColor: 'blue',
        lineType: 'both'
      }
    });

    // D. Approved Time-Off for this date
    const dayTimeoffs = this.allTimeoffs.filter((to: any) =>
      to.date === selectedIso &&
      (to.status === 'Approved' || to.status === 'Completed')
    );
    for (const to of dayTimeoffs) {
      const toStart = to.start_time ? this.formatTime12h(to.start_time) : lunchStart;
      const toEnd = to.end_time ? this.formatTime12h(to.end_time) : lunchEnd;
      const toMins = to.start_time ? (parseTimeToMinutes(this.formatTime12to24(to.start_time) || '') ?? 900) : 900;
      eventList.push({
        minutes: toMins,
        item: {
          time: toStart,
          title: 'Time Off',
          sub: `${to.leave_type || 'Approved'} (${to.duration_hours || 0} hrs)`,
          span: `${toStart} - ${toEnd}`,
          dotColor: 'purple',
          lineType: 'both'
        }
      });
    }

    // E. Punch Out (Actual if occurred)
    const effectivePunchOut = isToday ? this.punchOutTime : day?.punchOut;
    if (effectivePunchOut) {
      const punchOutDisplay = this.formatTime12h(effectivePunchOut);
      const punchOutMins = parseTimeToMinutes(this.formatTime12to24(effectivePunchOut) || '') ?? 1080;
      eventList.push({
        minutes: punchOutMins,
        item: {
          time: punchOutDisplay,
          title: 'Punch Out',
          sub: 'Shift Completed',
          span: `Out: ${punchOutDisplay}`,
          dotColor: 'purple',
          lineType: 'both'
        }
      });
    }

    // F. Shift Ends
    const shiftEndMins = parseTimeToMinutes(this.formatTime12to24(shiftEnd) || '18:00') ?? 1080;
    eventList.push({
      minutes: shiftEndMins,
      item: {
        time: shiftEnd,
        title: 'Shift Ends',
        sub: 'Scheduled End Time',
        span: 'End of Shift',
        dotColor: 'blue',
        lineType: 'up'
      }
    });

    // G. Active Overtime (if approved & applicable)
    if (isToday && this.overtimeApproved) {
      eventList.push({
        minutes: shiftEndMins + 1,
        item: {
          time: shiftEnd,
          title: 'Overtime',
          sub: 'Active Approved Overtime',
          span: `${shiftEnd} Onwards`,
          dotColor: 'green',
          lineType: 'up'
        }
      });
    }

    // Sort all events chronologically by minute of day
    eventList.sort((a, b) => a.minutes - b.minutes);

    // Set proper lineType connectors: first is 'down', middle are 'both', last is 'up'
    const sortedItems = eventList.map((ev, index) => {
      const it = { ...ev.item };
      if (index === 0) {
        it.lineType = 'down';
      } else if (index === eventList.length - 1) {
        it.lineType = 'up';
      } else {
        it.lineType = 'both';
      }
      return it;
    });

    return sortedItems;
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
    return [];
  }

  get todayIsoMin(): string {
    return toIsoDateLocal(new Date());
  }

  get previewRequestedHours(): number {
    if (this.timeOffLeaveType === 'Full Day') {
      return this.shiftTotalHours;
    }
    return this.shiftTotalHours / 2;
  }

  get previewRequestedSeconds(): number {
    if (this.timeOffLeaveType === 'Full Day') {
      return this.shiftTotalSeconds;
    }
    return (this.shiftTotalHours / 2) * 3600;
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
    const totalCircumference = 515; // 2 * PI * 82
    if (!this.isPunchedIn) {
      return totalCircumference * 0.75;
    }
    const targetSeconds = (this.shiftTotalHours || 9) * 3600;
    const progress = Math.min(1, Math.max(0.05, this.totalWorkedSecondsToday / targetSeconds));
    return Math.round(totalCircumference * (1 - progress));
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

  formatSecondsToHoursMinutes(seconds: number): string {
    if (!seconds || seconds <= 0) return '-';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const hStr = h < 10 ? `0${h}` : `${h}`;
    const mStr = m < 10 ? `0${m}` : `${m}`;
    return `${hStr}h ${mStr}m`;
  }

  get displayTimesheetRows(): DashboardTimesheetDisplayRow[] {
    const todayIso = toIsoDateLocal(new Date());

    let sourceRows: EmployeeTimesheetRow[] = [...this.filteredTimeSheets];

    // If today is not in sourceRows but the user has attendance state today, prepend today's entry
    if ((this.isPunchedIn || this.punchInTime) && !sourceRows.some(r => r.date === todayIso)) {
      const todayRow: EmployeeTimesheetRow = {
        date: todayIso,
        day: new Date().toLocaleDateString('en-GB', { weekday: 'short' }),
        entry: this.punchInTime || '-',
        exit: this.punchOutTime || '-',
        total: this.totalWorkedSecondsToday > 0 ? this.formatSecondsToHoursMinutes(this.totalWorkedSecondsToday) : '-',
        break: '01h 00m',
        overtime: '00h 00m',
        grandTotal: this.totalWorkedSecondsToday > 0 ? this.formatSecondsToHoursMinutes(this.totalWorkedSecondsToday) : '-',
        status: this.isPunchedIn ? 'Working' : (this.punchOutTime ? 'Present' : 'Working'),
        workMode: (this.status as WorkMode) || 'Office'
      };
      sourceRows = [todayRow, ...sourceRows];
    }

    if (!sourceRows || sourceRows.length === 0) {
      return [];
    }

    return sourceRows.slice(0, 3).map((row) => {
      const isToday = row.date === todayIso;
      const d = row.date ? new Date(row.date) : new Date();
      const dateFormatted = isNaN(d.getTime())
        ? row.date
        : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      const dayFormatted = isNaN(d.getTime())
        ? (row.day || '')
        : d.toLocaleDateString('en-GB', { weekday: 'short' });

      // Determine in/out times
      let inTime = this.formatTime12h(row.entry);
      let outTime = this.formatTime12h(row.exit);
      let workHours = this.formatDurationHm(row.total);

      if (isToday) {
        if (this.punchInTime) {
          inTime = this.formatTime12h(this.punchInTime);
        }
        if (this.punchOutTime) {
          outTime = this.formatTime12h(this.punchOutTime);
        }
        if (this.totalWorkedSecondsToday > 0) {
          workHours = this.formatSecondsToHoursMinutes(this.totalWorkedSecondsToday);
        } else if (this.isPunchedIn) {
          workHours = '< 1m';
        }
      }

      const statusStr = String(row.status || '');
      const isWorking = (isToday && this.isPunchedIn) || statusStr === 'Working';
      const isPresent = !isWorking && (statusStr === 'Present' || (isToday && !!this.punchOutTime));
      const isHoliday = statusStr === 'Holiday' || (!isToday && dayFormatted === 'Sun');
      const isAbsent = statusStr === 'Absent';
      const isTimeOff = statusStr === 'Time Off' || statusStr === 'Leave' || statusStr === 'Half Day';

      let statusClass = 'green-pill';
      let statusLabel = 'Present';
      if (isWorking) {
        statusClass = 'green-pill';
        statusLabel = 'Working';
      } else if (isHoliday) {
        statusClass = 'purple-pill';
        statusLabel = 'Holiday';
      } else if (isAbsent) {
        statusClass = 'red-pill';
        statusLabel = 'Absent';
      } else if (isTimeOff) {
        statusClass = 'orange-pill';
        statusLabel = 'Leave';
      } else if (isPresent) {
        statusClass = 'green-pill';
        statusLabel = 'Present';
      }

      return {
        date: dateFormatted,
        day: dayFormatted,
        inTime: inTime || '-',
        outTime: outTime || '-',
        workHours: workHours || '-',
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
    if (this.isAssignedRemoteWorker) {
      return;
    }
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
    if (this.isAssignedRemoteWorker) {
      this.showSwitchConfirmModal = false;
      return;
    }
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
    if (this.isAssignedRemoteWorker) {
      this.status = 'Remote';
      this.pendingPunchWorkMode = 'Remote';
    } else {
      this.pendingPunchWorkMode = this.status;
    }
    this.pendingPunchLatitude = undefined;
    this.pendingPunchLongitude = undefined;
    this.pendingPunchAddress = '';

    this.openCameraModal();
    this.fetchCurrentLocation();
  }

  setModalPunchWorkMode(mode: WorkMode): void {
    if (this.isAssignedRemoteWorker) {
      this.pendingPunchWorkMode = 'Remote';
      this.status = 'Remote';
      return;
    }
    this.pendingPunchWorkMode = mode;
    this.status = mode;
    if (this.pendingPunchLatitude != null && this.pendingPunchLongitude != null) {
      this.fetchCurrentLocation();
    }
    this.cdr.detectChanges();
  }

  fetchCurrentLocation(): void {
    this.isLocationLoading = true;
    this.punchMessage = 'Checking your office location...';
    this.cdr.detectChanges();

    const checkGeofenceAndProceed = (lat: number, lon: number) => {
      this.pendingPunchLatitude = lat;
      this.pendingPunchLongitude = lon;

      const isRemoteWorkMode = this.isAssignedRemoteWorker || this.pendingPunchWorkMode === 'Remote';
      const assignedName = (this.assignedWorkLocationName || '').trim().toLowerCase();
      const matchedLoc = this.masterWorkLocations.find(
        (l) => (l.name || '').trim().toLowerCase() === assignedName ||
               (l.code || '').trim().toLowerCase() === assignedName
      );

      const locType = matchedLoc?.location_type || (assignedName === 'remote' ? 'remote' : 'office');

      if (isRemoteWorkMode || locType === 'remote') {
        this.isLocationLoading = false;
        this.punchMessage = '';
        this.cdr.detectChanges();
        return;
      }

      if (matchedLoc && matchedLoc.latitude != null && matchedLoc.longitude != null) {
        const radius = matchedLoc.geofence_radius_meters || 40;
        const dist = this.calculateDistanceMeters(lat, lon, matchedLoc.latitude, matchedLoc.longitude);
        if (dist > radius) {
          this.punchMessage = `You are outside the assigned office location (${matchedLoc.name}) to mark attendance.`;
          this.isLocationLoading = false;
          this.cdr.detectChanges();
          return;
        }
      }

      this.isLocationLoading = false;
      this.punchMessage = '';
      this.cdr.detectChanges();
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          checkGeofenceAndProceed(pos.coords.latitude, pos.coords.longitude);
          this.attendanceService.reverseGeocode(pos.coords.latitude, pos.coords.longitude).subscribe({
            next: (geo: any) => {
              if (geo?.display_name) {
                this.pendingPunchAddress = geo.display_name;
              }
              this.cdr.detectChanges();
            },
            error: () => {}
          });
        },
        (err) => {
          console.warn('GPS location error:', err);
          const assignedName = (this.assignedWorkLocationName || '').trim();
          const matchedLoc = this.masterWorkLocations.find(
            (l) => l.name.toLowerCase() === assignedName.toLowerCase()
          );
          const locType = matchedLoc?.location_type || (assignedName.toLowerCase() === 'remote' ? 'remote' : 'office');
          if (locType === 'office') {
            this.punchMessage = `GPS location access is required to mark attendance for ${assignedName || 'your office'}. Please allow location permissions and try again.`;
          } else {
            this.punchMessage = '';
          }
          this.isLocationLoading = false;
          this.cdr.detectChanges();
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    } else {
      this.isLocationLoading = false;
      this.punchMessage = 'Geolocation is not supported by your browser.';
      this.cdr.detectChanges();
    }
  }

  private calculateDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371000.0;
    const phi1 = lat1 * Math.PI / 180;
    const phi2 = lat2 * Math.PI / 180;
    const deltaPhi = (lat2 - lat1) * Math.PI / 180;
    const deltaLambda = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
              Math.cos(phi1) * Math.cos(phi2) *
              Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
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
    this.isFaceDetected = false;
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
        video.onloadedmetadata = () => {
          video.play().then(() => {
            this.startFaceDetectionLoop(video);
          }).catch(() => {
            this.startFaceDetectionLoop(video);
          });
        };
      })
      .catch(() => {
        console.warn('Camera permission denied or camera unavailable');
        this.capturedImage = null;
        this.isFaceDetected = false;
        this.cdr.detectChanges();
      });
  }

  private startFaceDetectionLoop(video: HTMLVideoElement): void {
    this.stopFaceDetectionLoop();
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 48;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    this.faceDetectInterval = setInterval(async () => {
      if (!this.cameraStream || this.capturedImage || video.paused || video.ended) {
        return;
      }
      try {
        if ('FaceDetector' in window) {
          const detector = new (window as any).FaceDetector({ fastMode: true, maxDetectedFaces: 2 });
          const faces = await detector.detect(video);
          this.isFaceDetected = Array.isArray(faces) && faces.length > 0;
          this.cdr.detectChanges();
          return;
        }

        // Fast fallback heuristic based on central viewport luminance and skin distribution
        if (ctx && video.videoWidth > 0) {
          ctx.drawImage(video, 0, 0, 64, 48);
          const frame = ctx.getImageData(16, 12, 32, 24);
          const data = frame.data;
          let skinLikePixels = 0;
          const totalPixels = data.length / 4;

          for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            if (r > 50 && g > 30 && b > 15 && r > g && r > b && (r - g) > 8) {
              skinLikePixels++;
            }
          }

          this.isFaceDetected = (skinLikePixels / totalPixels) >= 0.10 || (video.readyState >= 3);
          this.cdr.detectChanges();
        } else {
          this.isFaceDetected = video.readyState >= 3;
          this.cdr.detectChanges();
        }
      } catch {
        this.isFaceDetected = video.readyState >= 3;
        this.cdr.detectChanges();
      }
    }, 300);
  }

  private stopFaceDetectionLoop(): void {
    if (this.faceDetectInterval) {
      clearInterval(this.faceDetectInterval);
      this.faceDetectInterval = null;
    }
  }

  private capturePhotoProgrammatically(video: HTMLVideoElement): string | null {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 320;
      canvas.height = video.videoHeight || 240;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        this.capturedImage = canvas.toDataURL('image/jpeg', 0.75);
        this.isFaceDetected = true;
        return this.capturedImage;
      }
    } catch (e) {
      console.error('Error capturing background photo:', e);
    }
    return null;
  }

  confirmPhoto(image: string | null = this.capturedImage): void {
    if (this.pendingPunchWorkMode === 'Office' && this.punchMessage) {
      return;
    }
    if (this.isLocationLoading) {
      return;
    }
    if (!this.isPunchedIn && !image) {
      const video = document.getElementById('cameraFeed') as HTMLVideoElement | null;
      image = video ? this.capturePhotoProgrammatically(video) : null;
    }
    this.isFaceDetected = true;
    this.executePunch(this.isPunchedIn ? null : image);
  }

  closeCameraModal(): void {
    this.stopCamera();
    this.showCameraModal = false;
    this.capturedImage = null;
    this.isFaceDetected = false;
    this.cdr.detectChanges();
  }

  private stopCamera(): void {
    this.stopFaceDetectionLoop();
    this.cameraStream?.getTracks().forEach(t => t.stop());
    this.cameraStream = null;
    this.isFaceDetected = false;
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

    let leaveTypeBackend = 'Half-Day';
    let startTimeBackend: string | null = null;
    let endTimeBackend: string | null = null;

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
          this.timeOffLeaveType === 'Full Day' ? 9.0 : 4.5
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
    const timeoffMapped: (DashboardRecentRequestItem & { sortDate: number })[] = (this.allTimeoffs || []).map((req: any) => {
      const statusLower = (req.status || 'Pending').toLowerCase();
      const isPending = statusLower === 'pending';
      const isApproved = ['approved', 'completed', 'active'].includes(statusLower);
      const isRejected = ['rejected', 'cancelled', 'expired'].includes(statusLower);

      let icon = 'far fa-calendar-alt';
      let iconBgClass = 'req-bg-blue';
      let iconColorClass = 'req-ic-blue';

      const typeLower = (req.leave_type || '').toLowerCase();
      if (typeLower.includes('sick')) {
        icon = 'far fa-user';
        iconBgClass = 'req-bg-amber';
        iconColorClass = 'req-ic-amber';
      } else if (typeLower.includes('casual')) {
        icon = 'far fa-calendar-alt';
        iconBgClass = 'req-bg-blue';
        iconColorClass = 'req-ic-blue';
      } else if (typeLower.includes('earned') || typeLower.includes('privilege')) {
        icon = 'far fa-calendar-check';
        iconBgClass = 'req-bg-green';
        iconColorClass = 'req-ic-green';
      } else if (typeLower.includes('home') || typeLower.includes('wfh') || typeLower.includes('remote')) {
        icon = 'far fa-calendar-minus';
        iconBgClass = 'req-bg-red';
        iconColorClass = 'req-ic-red';
      }

      const d = req.date ? new Date(req.date) : (req.created_at ? new Date(req.created_at) : new Date());
      const formattedDate = isNaN(d.getTime()) ? req.date : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });

      let durationLabel = '1 Day';
      if (req.duration_days) {
        durationLabel = `${req.duration_days} Day${req.duration_days > 1 ? 's' : ''}`;
      } else if (req.duration_hours) {
        durationLabel = `${req.duration_hours} hrs`;
      }

      return {
        icon,
        iconBgClass,
        iconColorClass,
        title: req.leave_type || 'Time Off Request',
        date: formattedDate,
        type: durationLabel,
        status: req.status || 'Pending',
        statusClass: isPending ? 'pending-pill' : (isApproved ? 'approved-pill' : (isRejected ? 'rejected-pill' : 'pending-pill')),
        sortDate: isNaN(d.getTime()) ? 0 : d.getTime()
      };
    });

    const regMapped: (DashboardRecentRequestItem & { sortDate: number })[] = (this.allRegularizations || []).map((reg: RegularizationRequestItem) => {
      const statusLower = (reg.status || 'pending').toLowerCase();
      const isPending = statusLower === 'pending';
      const isApproved = statusLower === 'approved';
      const isRejected = statusLower === 'rejected';

      const d = reg.attendanceDate ? new Date(reg.attendanceDate) : (reg.createdAt ? new Date(reg.createdAt) : new Date());
      const formattedDate = isNaN(d.getTime()) ? reg.attendanceDate : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });

      const reasonDisplay = (reg.reasonType || 'regularization')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());

      return {
        icon: 'far fa-file-alt',
        iconBgClass: 'req-bg-purple',
        iconColorClass: 'req-ic-purple',
        title: 'Regularization',
        date: formattedDate,
        type: reasonDisplay,
        status: isPending ? 'Pending' : (isApproved ? 'Approved' : 'Rejected'),
        statusClass: isPending ? 'pending-pill' : (isApproved ? 'approved-pill' : 'rejected-pill'),
        sortDate: isNaN(d.getTime()) ? 0 : d.getTime()
      };
    });

    const combined = [...timeoffMapped, ...regMapped].sort((a, b) => b.sortDate - a.sortDate);
    this.recentRequestsList = combined.slice(0, 4);
  }

  private ensureTimeSelectionsValid(): void {
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
        timesheets: this.attendanceService.getMyTimesheets().pipe(catchError(() => of([]))),
        timeoffs: this.timeoffService.getMyTimeOffRequests(1, 100).pipe(catchError(() => of({ items: [], totalItems: 0 } as any))),
        regularizations: this.regularizationService.getMyRequests(1, 100).pipe(catchError(() => of({ items: [], totalItems: 0 } as any))),
        masterData: this.masterDataService.getBootstrapData().pipe(catchError(() => of({ holidays: [], workLocations: [], leaveTypes: [] } as any))),
        leaveBalances: this.timeoffService.getMyLeaveBalances().pipe(catchError(() => of(null)))
      }).subscribe(({ timesheets, timeoffs, regularizations, masterData, leaveBalances }) => {
        const todayIso = this.toIsoDate(new Date());

        this.allTimesheets = timesheets || [];
        this.allTimeoffs = timeoffs?.items || [];
        this.allRegularizations = regularizations?.items || [];
        this.masterHolidays = masterData?.holidays || [];
        this.masterWorkLocations = masterData?.workLocations || [];

        this.subscriptions.add(
          this.myProfileService.getProfile().subscribe({
            next: (prof: any) => {
              this.assignedWorkLocationName = prof?.workLocation || prof?.employmentDetails?.workLocation || prof?.contactDetails?.location || prof?.employee?.workLocation || this.assignedWorkLocationName || '';
              if (this.isAssignedRemoteWorker) {
                this.status = 'Remote';
                this.pendingPunchWorkMode = 'Remote';
                this.pendingWorkModeToSwitch = 'Remote';
              }
              this.cdr.detectChanges();
            },
            error: () => {}
          })
        );

        const rawTimeoffItems = this.allTimeoffs;
        this.recentTimeOffRequests = rawTimeoffItems.slice(0, 5);
        this.updateRecentRequests();

        const pendingTimeoff = rawTimeoffItems.filter((req: any) => (req.status || '').toLowerCase() === 'pending').length;
        const pendingReg = this.allRegularizations.filter((reg: any) => (reg.status || '').toLowerCase() === 'pending').length;
        this.pendingRequestsCount = pendingTimeoff + pendingReg;

        // Populate leave balances from LeaveBalanceService
        if (leaveBalances?.yearlyBalances && leaveBalances.yearlyBalances.length > 0) {
          const dynamicItems: LeaveBalanceItem[] = [];
          for (const yb of leaveBalances.yearlyBalances) {
            const code = (yb.code || '').toUpperCase();
            const name = yb.name || code;
            const nameLower = name.toLowerCase();

            let initial = name.charAt(0).toUpperCase();
            let colorClass = 'indigo-icon';
            let textClass = 'indigo-days';

            if (code === 'CL' || nameLower.includes('casual')) {
              initial = 'C';
              colorClass = 'blue-icon';
              textClass = 'blue-days';
              this.casualLeaveBalanceDays = Math.round(Number(yb.available_days) || 0);
            } else if (code === 'SL' || nameLower.includes('sick')) {
              initial = 'S';
              colorClass = 'green-icon';
              textClass = 'green-days';
              this.sickLeaveBalanceDays = Math.round(Number(yb.available_days) || 0);
            } else if (code === 'EL' || nameLower.includes('earned') || nameLower.includes('privilege') || code === 'PL') {
              initial = 'E';
              colorClass = 'orange-icon';
              textClass = 'orange-days';
              this.earnedLeaveBalanceDays = Math.round(Number(yb.available_days) || 0);
            } else if (code === 'CO' || nameLower.includes('comp')) {
              initial = 'C';
              colorClass = 'amber-icon';
              textClass = 'amber-days';
            } else if (code === 'HD' || nameLower.includes('half')) {
              initial = 'H';
              colorClass = 'purple-icon';
              textClass = 'purple-days';
            } else if (code === 'WFH' || nameLower.includes('work from home') || nameLower.includes('remote')) {
              continue;
            } else if (code === 'ML' || nameLower.includes('maternity')) {
              initial = 'M';
              colorClass = 'rose-icon';
              textClass = 'rose-days';
            }

            dynamicItems.push({
              id: yb.leave_type_id,
              name: name,
              code: code,
              initial: initial,
              days: Math.round(Number(yb.available_days) || 0),
              colorClass: colorClass,
              textClass: textClass
            });
          }

          if (dynamicItems.length > 0) {
            this.leaveBalanceItems = dynamicItems;
          }
          this.leaveBalanceDays = Math.round(Number(leaveBalances.totalAvailableDays ?? this.totalAvailableLeaveDays) || 0);
        }

        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();

        const monthSheets = this.allTimesheets.filter((row: any) => {
          const d = new Date(row.date);
          return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
        });

        let presentCount = monthSheets.filter((row: any) => row.entry !== '-' || row.status === 'Present' || row.status === 'Late' || row.status === 'Working').length;
        const todayInMonthSheets = monthSheets.some((r: any) => r.date === todayIso);
        if (!todayInMonthSheets && (this.isPunchedIn || this.punchInTime)) {
          presentCount++;
        }
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
            if (req.leave_type === 'Half-Day' && req.start_time && req.end_time) {
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
    if (todayState.workLocationName) {
      this.assignedWorkLocationName = todayState.workLocationName;
    }
    if (this.isAssignedRemoteWorker || todayState.isRemoteWorker) {
      this.status = 'Remote';
      this.pendingPunchWorkMode = 'Remote';
      this.pendingWorkModeToSwitch = 'Remote';
    } else {
      this.status = todayState.workMode || 'Office';
    }
    this.punchInTime = this.formatTimeWithoutMicroseconds(todayState.punchIn);
    this.punchOutTime = this.formatTimeWithoutMicroseconds(todayState.punchOut);
    this.overtimeApproved = todayState.overtimeApproved || false;
    this.overtimeExtended = todayState.overtimeExtended || false;
    if (todayState.overtimeSeconds !== undefined) {
      this.overtimeSecondsToday = todayState.overtimeSeconds;
    }
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
    this.clearTrendHover();
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

  setTrendHover(pt: TrendDataPoint, index: number): void {
    this.hoveredTrendPoint = pt;
    this.hoveredTrendIndex = index;
    this.cdr.detectChanges();
  }

  clearTrendHover(): void {
    this.hoveredTrendPoint = null;
    this.hoveredTrendIndex = null;
    this.cdr.detectChanges();
  }

  getTrendTooltipLeft(x: number): number {
    return (x / 320) * 100;
  }

  updateAttendanceTrend(): void {
    const now = new Date();
    const todayIso = toIsoDateLocal(now);
    const targetSeconds = (this.shiftTotalHours || 9) * 3600;
    const targetMins = (this.shiftTotalHours || 9) * 60;

    // Calculate baseline from employee's actual timesheet history if available
    const pastRecordsWithTotal = (this.allTimesheets || []).filter(t => t.total && t.total !== '-');
    let historicalAvgPct = 88.4;
    if (pastRecordsWithTotal.length > 0) {
      const sumPcts = pastRecordsWithTotal.map(t => {
        const mins = this.parseDurationMinutes(t.total);
        return targetMins > 0 ? Math.min(100, Math.round((mins / targetMins) * 100)) : 85;
      });
      historicalAvgPct = Math.round(sumPcts.reduce((a, b) => a + b, 0) / sumPcts.length) || 88.4;
    }

    const xCoords = [15, 65, 115, 165, 215, 265, 305];
    const pcts: number[] = [];
    const points: { x: number; y: number }[] = [];
    const trendPoints: TrendDataPoint[] = [];
    const dayNames: string[] = [];

    if (this.trendPeriod === 'This Month') {
      const year = now.getFullYear();
      const month = now.getMonth();
      const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`;

      // Retrieve all records belonging to the current month sorted chronologically
      const monthSheets = (this.allTimesheets || [])
        .filter(t => t.date && t.date.startsWith(monthPrefix))
        .sort((a, b) => a.date.localeCompare(b.date));

      let targetDates: { iso: string; label: string; sheet?: EmployeeTimesheetRow }[] = [];

      if (monthSheets.length >= 7) {
        // Sample 7 evenly distributed actual records across the employee's month
        const step = (monthSheets.length - 1) / 6;
        for (let i = 0; i < 7; i++) {
          const idx = Math.round(i * step);
          const s = monthSheets[idx];
          const dObj = new Date(s.date);
          targetDates.push({
            iso: s.date,
            label: `${dObj.getDate()} ${this.getMonthName(month)}`,
            sheet: s
          });
        }
      } else if (monthSheets.length > 0) {
        // Less than 7 records: include all existing records first
        monthSheets.forEach(s => {
          const dObj = new Date(s.date);
          targetDates.push({
            iso: s.date,
            label: `${dObj.getDate()} ${this.getMonthName(month)}`,
            sheet: s
          });
        });
        // Pad with calendar dates to make 7 points if needed
        const lastDay = new Date(year, month + 1, 0).getDate();
        let dayNum = 1;
        while (targetDates.length < 7 && dayNum <= lastDay) {
          const iso = `${monthPrefix}-${String(dayNum).padStart(2, '0')}`;
          if (!targetDates.some(td => td.iso === iso)) {
            const dObj = new Date(year, month, dayNum);
            targetDates.push({
              iso,
              label: `${dayNum} ${this.getMonthName(month)}`,
              sheet: (this.allTimesheets || []).find(t => t.date === iso)
            });
          }
          dayNum += Math.max(1, Math.floor(lastDay / 7));
        }
        targetDates.sort((a, b) => a.iso.localeCompare(b.iso));
        targetDates = targetDates.slice(0, 7);
      } else {
        // Fallback when no month sheets exist yet: use 7 evenly spaced calendar days
        const lastDay = new Date(year, month + 1, 0).getDate();
        const daySteps = [1, Math.round(lastDay * 0.16), Math.round(lastDay * 0.33), Math.round(lastDay * 0.5), Math.round(lastDay * 0.67), Math.round(lastDay * 0.84), lastDay];
        for (let i = 0; i < 7; i++) {
          const dNum = daySteps[i];
          const currentD = new Date(year, month, dNum);
          const iso = toIsoDateLocal(currentD);
          targetDates.push({
            iso,
            label: `${dNum} ${this.getMonthName(month)}`,
            sheet: (this.allTimesheets || []).find(t => t.date === iso)
          });
        }
      }

      for (let i = 0; i < targetDates.length; i++) {
        const item = targetDates[i];
        const iso = item.iso;
        const dName = item.label;
        dayNames.push(dName);

        let dayPct = 0;
        let pointStatus = 'Scheduled';
        let pointDuration = '';

        const sheet = item.sheet || (this.allTimesheets || []).find(t => t.date === iso);
        const timeoff = (this.allTimeoffs || []).find(r => r.date === iso && ['Approved', 'Completed', 'Active'].includes(r.status));
        const currentD = new Date(iso);
        const isSun = currentD.getDay() === 0;
        const isHol = (this.masterHolidays || []).some(h => h.date === iso && h.is_active !== false);

        if (iso === todayIso && (this.isPunchedIn || this.punchInTime)) {
          if (this.isPunchedIn) {
            dayPct = targetSeconds > 0 ? Math.min(100, Math.round((this.totalWorkedSecondsToday / targetSeconds) * 1000) / 10) : 80;
            pointStatus = 'Working';
            pointDuration = this.liveTimerDisplay;
          } else {
            dayPct = targetSeconds > 0 ? Math.min(100, Math.round((this.totalWorkedSecondsToday / targetSeconds) * 1000) / 10) : 100;
            pointStatus = 'Present';
            pointDuration = this.totalWorkedTodayDisplay;
          }
        } else if (sheet && sheet.total && sheet.total !== '-') {
          pointDuration = sheet.total;
          const parsedMins = this.parseDurationMinutes(sheet.total);
          dayPct = targetMins > 0 ? Math.min(100, Math.round((parsedMins / targetMins) * 1000) / 10) : 85;
          pointStatus = sheet.status || 'Present';
        } else if (timeoff) {
          dayPct = 100;
          pointStatus = 'Leave';
          pointDuration = 'Full Day';
        } else if (sheet && (sheet.status === 'Present' || sheet.status === 'Working')) {
          dayPct = 100;
          pointStatus = 'Present';
          pointDuration = `${this.shiftTotalHours || 9}h 00m`;
        } else if (sheet && (sheet.status === 'Half Day' || sheet.status === 'Time Off')) {
          dayPct = 50;
          pointStatus = 'Half Day';
          pointDuration = '4h 00m';
        } else if (isHol || isSun) {
          dayPct = 0;
          pointStatus = 'Holiday';
          pointDuration = 'Off';
        } else {
          dayPct = 0;
          pointStatus = iso > todayIso ? 'Scheduled' : (sheet?.status || 'Not Marked');
          pointDuration = '-';
        }

        pcts.push(dayPct);
        const y = Math.round(85 - ((dayPct / 100) * 75));
        const x = xCoords[i];
        points.push({ x, y });
        trendPoints.push({
          day: dName,
          dateStr: iso,
          pct: dayPct,
          x,
          y,
          label: `${dayPct.toFixed(1)}%`,
          status: pointStatus,
          duration: pointDuration
        });
      }
    } else {
      // 'This Week' or 'Last Week'
      const dayOfWeek = now.getDay();
      const mondayOffset = (dayOfWeek + 6) % 7;

      let startMonday = new Date(now);
      startMonday.setDate(now.getDate() - mondayOffset);

      if (this.trendPeriod === 'Last Week') {
        startMonday.setDate(startMonday.getDate() - 7);
      }

      const standardDayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

      for (let i = 0; i < 7; i++) {
        const currentD = new Date(startMonday);
        currentD.setDate(startMonday.getDate() + i);
        const iso = toIsoDateLocal(currentD);
        const dayName = standardDayNames[i];
        dayNames.push(dayName);

        let dayPct = 0;
        let pointStatus = 'Scheduled';
        let pointDuration = '';

        const sheet = (this.allTimesheets || []).find(t => t.date === iso);
        const timeoff = (this.allTimeoffs || []).find(r => r.date === iso && ['Approved', 'Completed', 'Active'].includes(r.status));
        const isSun = currentD.getDay() === 0;
        const isHol = (this.masterHolidays || []).some(h => h.date === iso && h.is_active !== false);

        if (iso === todayIso && (this.isPunchedIn || this.punchInTime)) {
          if (this.isPunchedIn) {
            dayPct = targetSeconds > 0 ? Math.min(100, Math.round((this.totalWorkedSecondsToday / targetSeconds) * 1000) / 10) : 80;
            pointStatus = 'Working';
            pointDuration = this.liveTimerDisplay;
          } else {
            dayPct = targetSeconds > 0 ? Math.min(100, Math.round((this.totalWorkedSecondsToday / targetSeconds) * 1000) / 10) : 100;
            pointStatus = 'Present';
            pointDuration = this.totalWorkedTodayDisplay;
          }
        } else if (sheet && sheet.total && sheet.total !== '-') {
          pointDuration = sheet.total;
          const parsedMins = this.parseDurationMinutes(sheet.total);
          dayPct = targetMins > 0 ? Math.min(100, Math.round((parsedMins / targetMins) * 1000) / 10) : 85;
          pointStatus = sheet.status || 'Present';
        } else if (timeoff) {
          dayPct = 100;
          pointStatus = 'Leave';
          pointDuration = 'Full Day';
        } else if (sheet && (sheet.status === 'Present' || sheet.status === 'Working')) {
          dayPct = 100;
          pointStatus = 'Present';
          pointDuration = `${this.shiftTotalHours || 9}h 00m`;
        } else if (sheet && (sheet.status === 'Half Day' || sheet.status === 'Time Off')) {
          dayPct = 50;
          pointStatus = 'Half Day';
          pointDuration = '4h 00m';
        } else if (isHol || isSun) {
          dayPct = 0;
          pointStatus = 'Holiday';
          pointDuration = 'Off';
        } else {
          dayPct = 0;
          pointStatus = iso > todayIso ? 'Scheduled' : (sheet?.status || 'Not Marked');
          pointDuration = '-';
        }

        pcts.push(dayPct);
        const y = Math.round(85 - ((dayPct / 100) * 75));
        const x = xCoords[i];
        points.push({ x, y });
        trendPoints.push({
          day: dayName,
          dateStr: iso,
          pct: dayPct,
          x,
          y,
          label: `${dayPct.toFixed(1)}%`,
          status: pointStatus,
          duration: pointDuration
        });
      }
    }

    this.trendDataPoints = trendPoints;
    this.trendLinePathD = this.buildSmoothPath(points);
    this.trendAreaPathD = points.length > 0
      ? `${this.trendLinePathD} L ${xCoords[points.length - 1]} 95 L ${xCoords[0]} 95 Z`
      : '';

    // Compute stats purely from employee's actual attendance records
    if (this.trendPeriod === 'This Month') {
      const year = now.getFullYear();
      const month = now.getMonth();
      const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`;
      const monthSheets = (this.allTimesheets || []).filter(t => t.date && t.date.startsWith(monthPrefix));

      const monthPcts: { date: string; pct: number; label: string }[] = [];
      for (const s of monthSheets) {
        let p = 0;
        if (s.total && s.total !== '-') {
          const parsed = this.parseDurationMinutes(s.total);
          p = targetMins > 0 ? Math.min(100, Math.round((parsed / targetMins) * 1000) / 10) : 85;
        } else if (s.status === 'Present' || s.status === 'Working') {
          p = 100;
        } else if (s.status === 'Half Day' || s.status === 'Time Off') {
          p = 50;
        }
        if (p > 0) {
          const dObj = new Date(s.date);
          const dName = `${dObj.getDate()} ${this.getMonthName(month)}`;
          monthPcts.push({ date: s.date, pct: p, label: dName });
        }
      }

      if (monthPcts.length > 0) {
        const avg = monthPcts.reduce((sum, item) => sum + item.pct, 0) / monthPcts.length;
        this.trendAvgThisWeek = `${avg.toFixed(1)}%`;

        let best = monthPcts[0];
        let lowest = monthPcts[0];
        for (const item of monthPcts) {
          if (item.pct > best.pct) best = item;
          if (item.pct < lowest.pct) lowest = item;
        }
        this.trendBestDay = `${best.pct.toFixed(1)}%`;
        this.trendBestDayName = best.label;
        this.trendLowestDay = `${lowest.pct.toFixed(1)}%`;
        this.trendLowestDayName = lowest.label;
      } else {
        this.trendAvgThisWeek = '0.0%';
        this.trendBestDay = '0.0%';
        this.trendBestDayName = '-';
        this.trendLowestDay = '0.0%';
        this.trendLowestDayName = '-';
      }
    } else {
      // 'This Week' or 'Last Week'
      const workedPcts = pcts.filter((p, idx) => {
        const pt = trendPoints[idx];
        return pt && pt.status !== 'Scheduled' && p > 0;
      });

      const avg = workedPcts.length > 0
        ? (workedPcts.reduce((sum, p) => sum + p, 0) / workedPcts.length)
        : 0.0;

      this.trendAvgThisWeek = `${avg.toFixed(1)}%`;

      let maxIdx = -1;
      let minIdx = -1;
      for (let i = 0; i < pcts.length; i++) {
        if (trendPoints[i]?.status === 'Scheduled') continue;
        if (pcts[i] > 0) {
          if (maxIdx === -1 || pcts[i] > pcts[maxIdx]) maxIdx = i;
          if (minIdx === -1 || pcts[i] < pcts[minIdx]) minIdx = i;
        }
      }

      this.trendBestDay = maxIdx !== -1 ? `${pcts[maxIdx].toFixed(1)}%` : '0.0%';
      this.trendBestDayName = maxIdx !== -1 ? dayNames[maxIdx] : '-';
      this.trendLowestDay = minIdx !== -1 ? `${pcts[minIdx].toFixed(1)}%` : '0.0%';
      this.trendLowestDayName = minIdx !== -1 ? dayNames[minIdx] : '-';
    }
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
