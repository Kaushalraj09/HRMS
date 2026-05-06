import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Injectable, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { CalendarModule, CalendarDateFormatter, CalendarNativeDateFormatter, DateFormatterParams } from 'angular-calendar';
import { CalendarEvent } from 'calendar-utils';
import { finalize, Subscription } from 'rxjs';

import { AttendanceService } from '../../../../core/services/attendance.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TimeEngineService } from '../../../../core/services/time-engine.service';
import {
  EmployeeAttendanceSummaryItem,
  EmployeeTimelineEvent,
  EmployeeTimesheetRow,
  TodayAttendanceState,
  WorkMode
} from '../../../../core/models/attendance.model';
import {
  SHIFT_TOTAL_HOURS,
  TimeSlotOption,
  buildHalfHourSlots,
  filterSlotsNotBeforeNow,
  hoursBetweenSameDay,
  parseTimeToMinutes,
  safeNumber,
  toIsoDateLocal
} from '../../../../core/utils/timeoff-time.util';
import {
  SHIFT_TOTAL_SECONDS,
  clampSeconds,
  formatSecondsToClock
} from '../../../../core/utils/attendance-time.util';
import { SharedModule } from '../../../../shared/shared-module';
import { EmpSidebar } from '../../components/emp-sidebar/emp-sidebar';
import { EmpSidebarService } from '../../components/emp-sidebar/emp-sidebar.service';

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
    SharedModule,
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
export class EmpDashboard implements OnDestroy {
  selectedLang = 'en';
  userName = 'Employee';
  currentDate = new Date();
  status: WorkMode = 'Office';
  isEmpSidebarOpen$!: import('rxjs').Observable<boolean>;
  isDashboardHome = true;

  isPunchedIn = false;
  punchInTime: string | null = null;
  punchOutTime: string | null = null;
  isPunchSaving = false;
  punchMessage = '';
  attendanceStatusLabel = 'Not working';

  approvedHours = 0;
  remainingHours = SHIFT_TOTAL_HOURS;
  approvedSecondsToday = 0;
  remainingSecondsToday = SHIFT_TOTAL_SECONDS;
  totalWorkedSecondsToday = 0;
  shiftElapsedSeconds = 0;
  shiftProgress = 0;
  liveTimerDisplay = formatSecondsToClock(0);
  lateMinutes = 0;
  earlyLeaveMinutes = 0;
  overtimeMinutes = 0;

  readonly shiftTotalHours = SHIFT_TOTAL_HOURS;
  readonly shiftTotalSeconds = SHIFT_TOTAL_SECONDS;
  readonly allTimeSlots: TimeSlotOption[] = buildHalfHourSlots();

  timeOffDate = toIsoDateLocal(new Date());
  timeOffLeaveType: 'Hourly' | 'Full Day' = 'Hourly';
  timeOffStart = '09:00';
  timeOffEnd = '10:00';
  isTimeOffSubmitting = false;
  timeOffInlineError = '';

  timeSheets: EmployeeTimesheetRow[] = [];
  attendanceSummary: EmployeeAttendanceSummaryItem[] = [];
  viewDate = new Date();
  selectedDate = new Date();
  weekNumber = 2;
  timelineEvents: EmployeeTimelineEvent[] = [];
  calendarEvents: CalendarEvent[] = [];
  selectedEvents: EmployeeTimelineEvent[] = [];

  showScheduleModal = false;
  scheduleForm = {
    date: new Date().toISOString().slice(0, 10),
    startTime: '09:00',
    workMode: 'Office' as WorkMode,
    taskDescription: ''
  };

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
    private readonly authService: AuthService,
    private readonly timeEngine: TimeEngineService,
    private readonly cdr: ChangeDetectorRef
  ) {
    this.isEmpSidebarOpen$ = this.empsidebarService.isEmpSidebarOpen$;
    this.isDashboardHome = this.router.url === '/emp-dashboard';
    this.userName = this.authService.getDisplayName();

    this.subscriptions.add(
      this.router.events.subscribe((event) => {
        if (event instanceof NavigationEnd) {
          this.isDashboardHome = event.urlAfterRedirects === '/emp-dashboard';
        }
      })
    );

    this.subscriptions.add(
      this.timeEngine.state$.subscribe((state) => {
        if (!state) return;
        this.applyTodayState(state);
        this.cdr.detectChanges();
      })
    );

    this.initialize();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  toggleSidebar() {
    this.empsidebarService.toggleSidebar();
  }

  onSearch(event: unknown) {
    console.log('Search:', event);
  }

  openProfile() {
    console.log('Opening profile');
  }

  openNotifications() {
    console.log('Opening notifications');
  }

  get punchActionLabel(): string {
    return this.isPunchedIn ? 'Punch Out' : 'Punch In';
  }

  get isPunchDisabled(): boolean {
    return this.isPunchSaving;
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
      return SHIFT_TOTAL_HOURS;
    }
    return hoursBetweenSameDay(this.timeOffStart, this.timeOffEnd);
  }

  get previewRequestedSeconds(): number {
    if (this.timeOffLeaveType === 'Full Day') {
      return SHIFT_TOTAL_SECONDS;
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

  get canSubmitInlineTimeOff(): boolean {
    if (this.isTimeOffSubmitting || !this.isPunchedIn) {
      return false;
    }
    if (this.timeOffLeaveType === 'Full Day') {
      return this.remainingSecondsToday >= SHIFT_TOTAL_SECONDS;
    }
    return this.previewRequestedSeconds > 0 && this.previewRequestedSeconds <= this.remainingSecondsToday;
  }

  get progressDashOffset(): number {
    return 100 - Math.round(this.shiftProgress * 100);
  }

  togglePunch(): void {
    if (this.isPunchDisabled) {
      return;
    }

    this.isPunchSaving = true;
    this.punchMessage = '';

    const request$ = this.isPunchedIn
      ? this.attendanceService.punchOut(this.status)
      : this.attendanceService.punchIn(this.status);

    this.subscriptions.add(
      request$
        .pipe(finalize(() => { this.isPunchSaving = false; }))
        .subscribe({
          next: (todayState: TodayAttendanceState) => {
            this.applyTodayState(todayState);
            this.loadDashboardData();
          },
          error: (error) => {
            this.punchMessage = error?.error?.detail || 'Unable to update attendance right now.';
            this.cdr.detectChanges();
          }
        })
    );
  }

  onLeaveTypeChange(): void {
    this.timeOffInlineError = '';
    if (this.timeOffLeaveType === 'Full Day') {
      this.timeOffStart = '09:00';
      this.timeOffEnd = '18:00';
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
    if (!this.canSubmitInlineTimeOff) {
      this.timeOffInlineError = this.isPunchedIn
        ? 'Requested time must fit inside your remaining shift balance.'
        : 'You can apply time off only while marked as Working.';
      return;
    }

    this.isTimeOffSubmitting = true;
    this.subscriptions.add(
      this.attendanceService
        .applyTimeOffInline({
          date: this.timeOffDate,
          leave_type: this.timeOffLeaveType,
          start_time: this.timeOffLeaveType === 'Full Day' ? null : this.timeOffStart,
          end_time: this.timeOffLeaveType === 'Full Day' ? null : this.timeOffEnd
        })
        .pipe(finalize(() => { this.isTimeOffSubmitting = false; }))
        .subscribe({
          next: (response) => {
            this.approvedHours = safeNumber(response.approved_hours_today, 0);
            this.remainingHours = safeNumber(response.remaining_hours_today, 0);
            this.approvedSecondsToday = safeNumber(response.approved_seconds_today, 0);
            this.remainingSecondsToday = safeNumber(response.remaining_seconds_today, 0);
            this.loadDashboardData();
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
  }

  getWeekOfMonth(date: Date): number {
    const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
    const dayOfWeek = firstDayOfMonth.getDay();
    return Math.ceil((date.getDate() + dayOfWeek) / 7);
  }

  filterEvents(date: Date) {
    const isoDate = this.toIsoDate(date);
    this.selectedEvents = this.timelineEvents
      .filter((event) => event.date === isoDate)
      .sort((left, right) => this.eventSortValue(left.time) - this.eventSortValue(right.time));
  }

  private initialize(): void {
    this.weekNumber = this.getWeekOfMonth(this.selectedDate);
    this.loadDashboardData();

    const user = this.authService.getCurrentUser();
    if (user) {
      this.attendanceService.connectWebSocket(user.id);
    }

    this.subscriptions.add(
      this.attendanceService.timeoffUpdate$.subscribe((data) => {
        alert(data.message);
        this.loadDashboardData();
      })
    );
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
      this.attendanceService.getMyTimesheets().subscribe((rows: EmployeeTimesheetRow[]) => {
        const todayIso = this.toIsoDate(new Date());
        this.timeSheets = rows.filter((row) =>
          row.date <= todayIso
          && (
            row.entry !== '-'
            || row.exit !== '-'
            || !!row.scheduledStart
            || !!row.scheduledEnd
            || !!row.taskDescription
          )
        );

        this.timelineEvents = rows.flatMap((row: EmployeeTimesheetRow) => {
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
            events.push({ date: row.date, time: row.entry, title: 'Punch In', location: 'Office', type: 'punch-in' });
          }

          if (row.exit !== '-') {
            events.push({ date: row.date, time: row.exit, title: 'Punch Out', location: 'Office', type: 'punch-out' });
          }

          return events;
        });

        this.calendarEvents = this.timelineEvents.map((event) => ({
          start: new Date(`${event.date}T00:00:00`),
          title: event.title,
          color: {
            primary: event.type === 'schedule' ? '#2563eb' : '#16a34a',
            secondary: event.type === 'schedule' ? '#dbeafe' : '#dcfce7'
          }
        }));

        this.filterEvents(this.selectedDate);
        this.cdr.detectChanges();
      })
    );

    this.subscriptions.add(
      this.attendanceService.getMyAttendanceSummary().subscribe((summary: EmployeeAttendanceSummaryItem[]) => {
        this.attendanceSummary = summary;
        this.cdr.detectChanges();
      })
    );
  }

  private applyTodayState(todayState: TodayAttendanceState): void {
    this.isPunchedIn = todayState.isWorking;
    this.approvedSecondsToday = todayState.approvedSeconds;
    this.remainingSecondsToday = todayState.remainingSeconds;
    this.totalWorkedSecondsToday = todayState.totalWorkedSeconds;
    this.shiftElapsedSeconds = todayState.shiftElapsedSeconds;
    this.shiftProgress = todayState.shiftTotalSeconds > 0 ? (todayState.shiftElapsedSeconds / todayState.shiftTotalSeconds) : 0;
    this.attendanceStatusLabel = todayState.isWorking ? 'Working' : 'Not Working';
    this.status = todayState.workMode;
    this.punchInTime = todayState.checkIn || null;
    this.punchOutTime = todayState.checkOut || null;
    this.liveTimerDisplay = this.timeEngine.formatHHMMSS(this.shiftElapsedSeconds);
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

  private formatMinutesCompact(minutes: number): string {
    const safeMinutes = Math.max(0, Math.floor(safeNumber(minutes, 0)));
    const hours = Math.floor(safeMinutes / 60);
    const mins = safeMinutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  }
}
