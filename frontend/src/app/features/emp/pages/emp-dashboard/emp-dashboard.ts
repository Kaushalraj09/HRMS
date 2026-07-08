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
import { Navbar } from '../../../../shared/components/navbar/navbar';
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
  remainingHours = SHIFT_TOTAL_HOURS;
  approvedSecondsToday = 0;
  remainingSecondsToday = SHIFT_TOTAL_SECONDS;
  totalWorkedSecondsToday = 0;
  shiftElapsedSeconds = 0;
  shiftProgress = 0;
  lateMinutes = 0;
  earlyLeaveMinutes = 0;
  overtimeMinutes = 0;

  readonly shiftTotalHours = SHIFT_TOTAL_HOURS;
  readonly shiftTotalSeconds = SHIFT_TOTAL_SECONDS;
  readonly allTimeSlots: TimeSlotOption[] = buildHalfHourSlots();

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
  selectedEvents: EmployeeTimelineEvent[] = [];

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
    console.log('Opening profile');
  }

  get punchActionLabel(): string {
    return this.isPunchedIn ? 'Punch Out' : 'Punch In';
  }

  get isPunchDisabled(): boolean {
    return this.isPunchSaving || !!this.punchOutTime || this.isAdmin;
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
      return SHIFT_TOTAL_HOURS;
    }
    if (this.timeOffLeaveType === 'Half Day') {
      return 4.0;
    }
    return hoursBetweenSameDay(this.timeOffStart, this.timeOffEnd);
  }

  get previewRequestedSeconds(): number {
    if (this.timeOffLeaveType === 'Full Day') {
      return SHIFT_TOTAL_SECONDS;
    }
    if (this.timeOffLeaveType === 'Half Day') {
      return 4.0 * 3600;
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
        return this.previewRequestedSeconds > 0 && this.previewRequestedSeconds <= SHIFT_TOTAL_SECONDS;
      }
      return true;
    }
    if (!this.isPunchedIn) {
      return false;
    }
    if (this.timeOffLeaveType === 'Full Day') {
      return this.remainingSecondsToday >= SHIFT_TOTAL_SECONDS;
    }
    return this.previewRequestedSeconds > 0 && this.previewRequestedSeconds <= this.remainingSecondsToday;
  }

  get progressDashOffset(): number {
    const progress = Math.min(1, Math.max(0, this.shiftProgress));
    return 100 - Math.round(progress * 100);
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
              this.pendingPunchAddress = [city, region, country].filter(val => !!val).join(', ');
            } else {
              this.pendingPunchLatitude = undefined;
              this.pendingPunchLongitude = undefined;
              this.pendingPunchAddress = 'Location Unavailable';
            }
            this.isLocationLoading = false;
            this.cdr.detectChanges();
          },
          error: () => {
            this.pendingPunchLatitude = undefined;
            this.pendingPunchLongitude = undefined;
            this.pendingPunchAddress = 'Location Unavailable';
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
              this.pendingPunchAddress = geo?.display_name || '';
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
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
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
    this.closeCameraModal();
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
        .pipe(finalize(() => { this.isPunchSaving = false; }))
        .subscribe({
          next: (todayState: TodayAttendanceState) => {
            this.applyTodayState(todayState);
            this.loadDashboardData();
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

  onLeaveTypeChange(): void {
    this.timeOffInlineError = '';
    if (this.timeOffLeaveType === 'Full Day') {
      this.timeOffStart = '09:00';
      this.timeOffEnd = '18:00';
    } else if (this.timeOffLeaveType === 'Half Day') {
      this.timeOffHalfDaySession = 'First Half';
      this.timeOffStart = '09:00';
      this.timeOffEnd = '13:00';
    } else {
      this.timeOffStart = '09:00';
      this.timeOffEnd = '10:00';
    }
  }

  onHalfDaySessionChange(): void {
    this.timeOffInlineError = '';
    if (this.timeOffHalfDaySession === 'First Half') {
      this.timeOffStart = '09:00';
      this.timeOffEnd = '13:00';
    } else {
      this.timeOffStart = '14:00';
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
      if (this.timeOffHalfDaySession === 'First Half') {
        startTimeBackend = '09:00';
        endTimeBackend = '13:00';
      } else {
        startTimeBackend = '14:00';
        endTimeBackend = '18:00';
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
            this.timeOffInlineSuccess = 'Time off request submitted to HR for approval.';
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

    // this.subscriptions.add(
    //   this.attendanceService.timeoffUpdate$.subscribe((data) => {
    //     alert(data.message);
    //     this.loadDashboardData();
    //   })
    // );
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
        timeoffs: this.timeoffService.getMyTimeOffRequests()
      }).subscribe(({ timesheets, timeoffs }) => {
        const todayIso = this.toIsoDate(new Date());
        
        // Filter timesheets for display in the table (history only)
        this.timeSheets = timesheets.filter((row) =>
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
        const timesheetEvents = timesheets.flatMap((row: EmployeeTimesheetRow) => {
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
          { label: 'Total Days', value: timesheets.length, icon: 'fas fa-calendar total blue-icon' },
          { label: 'Worked Days', value: timesheets.filter(row => row.status !== 'Not Marked').length, icon: 'fas fa-calendar-check worked blue-icon' },
          { label: 'Present', value: timesheets.filter(row => row.status === 'Present').length, icon: 'fas fa-check-circle blue-icon' },
          { label: 'Working', value: timesheets.filter(row => row.status === 'Working').length, icon: 'fas fa-user-check blue-icon' },
          { label: 'Absent', value: timesheets.filter(row => row.status === 'Absent').length, icon: 'fas fa-times-circle red-icon' },
          { label: 'Not Marked', value: timesheets.filter(row => row.status === 'Not Marked').length, icon: 'fas fa-user-times unapproved gold-icon' }
        ];

        this.filterEvents(this.selectedDate);
        this.cdr.detectChanges();
      })
    );
  }

  get isShiftEndReminderActive(): boolean {
    if (!this.isPunchedIn || this.overtimeApproved || this.punchOutTime) {
      return false;
    }
    if (this.wsShiftEndReminderActive) {
      return true;
    }
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    const currentMinutesOfDay = currentHour * 60 + currentMinute;
    return currentMinutesOfDay >= 1085; // >= 18:05
  }

  get isOvertimeReminderActive(): boolean {
    if (!this.isPunchedIn || !this.overtimeApproved || this.overtimeExtended || this.punchOutTime) {
      return false;
    }
    if (this.wsOvertimeReminderActive) {
      return true;
    }
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    const currentMinutesOfDay = currentHour * 60 + currentMinute;
    return currentMinutesOfDay >= 1200; // >= 20:00
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
        this.successMessage = "Overtime session started successfully. You can work until 8:00 PM.";
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
        this.successMessage = "Overtime extended successfully. You can work until 10:00 PM.";
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
    // Preserve first image; only update if not already set
    if (todayState.punchInImage) { this.punchInImage = todayState.punchInImage; }
    if (todayState.punchOutImage) { this.punchOutImage = todayState.punchOutImage; }
    if (todayState.punchInAddress) { this.punchInAddress = todayState.punchInAddress; }
    if (todayState.punchOutAddress) { this.punchOutAddress = todayState.punchOutAddress; }
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
}
