import { Component, OnInit, OnDestroy, EventEmitter, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { AttendanceService } from '../../../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../../../core/services/timeoff.service';
import { TodayAttendanceState } from '../../../../../../core/models/attendance.model';
import { YearlyLeaveBalance } from '../../../../../../core/models/timeoff.model';
import {
  TimeSlotOption,
  buildHalfHourSlots,
  filterSlotsNotBeforeNow,
  hoursBetweenSameDay,
  parseTimeToMinutes,
  toIsoDateLocal
} from '../../../../../../core/utils/timeoff-time.util';

import { CustomDatepickerComponent } from '../../../../../../shared/components/custom-datepicker/custom-datepicker';
import { CustomSelectComponent } from '../../../../../../shared/components/custom-select/custom-select';
import { ToastService } from '../../../../../../core/services/toast.service';
import { MasterDataService } from '../../../../../../core/services/master-data.service';

@Component({
  selector: 'app-time-off-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, CustomDatepickerComponent, CustomSelectComponent],
  templateUrl: './time-off-modal.html',
  styleUrls: ['./time-off-modal.css']
})
export class TimeOffModalComponent implements OnInit, OnDestroy {
  @Output() closed = new EventEmitter<boolean>();

  leaveForm!: FormGroup;
  isSubmitting = false;
  successMessage = '';
  errorMessage = '';

  yearlyBalances: YearlyLeaveBalance[] = [];
  selectedLeaveBalance: YearlyLeaveBalance | null = null;
  isRemoteEmployee = false;
  isWfhSelected = false;

  // File upload state
  uploadedFileName = '';
  uploadedFileSize = '';
  uploadProgress = 0;
  isDragOver = false;

  shiftStart24 = '09:00';
  shiftEnd24 = '18:00';
  firstHalfStart24 = '09:00';
  firstHalfEnd24 = '13:00';
  secondHalfStart24 = '14:00';
  secondHalfEnd24 = '18:00';
  halfDayDurationHours = 4.0;
  fullDayDurationHours = 9.0;

  readonly allTimeSlots: TimeSlotOption[] = buildHalfHourSlots();

  leaveTypeSelectOptions: { label: string; value: string; unitType?: string }[] = [
    { label: 'Casual Leave (Full Day)', value: 'Casual Leave', unitType: 'full_day' },
    { label: 'Sick Leave (Full Day)', value: 'Sick Leave', unitType: 'full_day' },
    { label: 'Earned Leave (Full Day)', value: 'Earned Leave', unitType: 'full_day' },
    { label: 'Full Day Leave', value: 'Full Day', unitType: 'full_day' },
    { label: 'Half Day Leave', value: 'Half Day', unitType: 'half_day' },
    { label: 'Hourly Time Off', value: 'Hourly', unitType: 'hourly' }
  ];

  halfDaySessionSelectOptions: { label: string; value: string }[] = [
    { label: 'First Half (09:00 AM - 01:00 PM)', value: 'First Half' },
    { label: 'Second Half (02:00 PM - 06:00 PM)', value: 'Second Half' }
  ];

  private subscriptions = new Subscription();

  constructor(
    private readonly fb: FormBuilder,
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly cdr: ChangeDetectorRef,
    private readonly toastService: ToastService,
    private readonly masterDataService: MasterDataService
  ) {}

  ngOnInit(): void {
    const today = toIsoDateLocal(new Date());

    this.leaveForm = this.fb.group({
      leaveType: ['Hourly', Validators.required],
      startDate: [today, Validators.required],
      multipleDays: [false],
      endDate: [today],
      halfDaySession: ['First Half'],
      startTime: ['09:00'],
      endTime: ['10:00'],
      reason: ['', [Validators.required, Validators.maxLength(500)]]
    });

    // Load dynamic leave types from Master Data
    this.subscriptions.add(
      this.masterDataService.getBootstrapData().subscribe({
        next: (data) => {
          const rawLeaveTypes = data?.leaveTypes || (data as any)?.leave_types || [];
          const activeLeaveTypes = rawLeaveTypes.filter((l: any) => l && l.is_active !== false);

          if (activeLeaveTypes.length > 0) {
            // Priority sort: Casual (CL) -> Sick (SL) -> Earned/Privilege (EL/PL) -> Comp Off (CO) -> Half Day (HD) -> Work From Home (WFH) -> Others
            const getPriority = (item: any) => {
              const code = (item.code || '').toUpperCase();
              const name = (item.name || '').toLowerCase();
              if (code === 'CL' || name.includes('casual')) return 1;
              if (code === 'SL' || name.includes('sick')) return 2;
              if (code === 'EL' || name.includes('earned') || name.includes('privilege') || code === 'PL') return 3;
              if (code === 'CO' || name.includes('comp')) return 4;
              if (code === 'HD' || name.includes('half')) return 5;
              if (code === 'WFH' || name.includes('work from home') || name.includes('remote')) return 6;
              return 7;
            };
            activeLeaveTypes.sort((a: any, b: any) => getPriority(a) - getPriority(b));

            const dynamicOptions: { label: string; value: string; unitType?: string }[] = [];
            let hasHalfDay = false;

            for (const lt of activeLeaveTypes) {
              const code = (lt.code || '').toUpperCase();
              const name = (lt.name || code).trim();
              const nameLower = name.toLowerCase();
              const unit = (lt.unit_type || '').toLowerCase();
              const isHalf = unit === 'half_day' || code === 'HD' || nameLower.includes('half');
              const isHourly = unit === 'hourly' || code === 'HOURLY' || nameLower.includes('hourly');

              if (isHalf) {
                hasHalfDay = true;
                const label = nameLower.includes('leave') ? name : `${name} Leave`;
                dynamicOptions.push({
                  label,
                  value: name,
                  unitType: 'half_day'
                });
              } else if (isHourly) {
                dynamicOptions.push({
                  label: name,
                  value: name,
                  unitType: 'hourly'
                });
              } else {
                // Full Day type
                let label = name;
                if (!nameLower.includes('full day') && !nameLower.includes('(full day)')) {
                  if (code === 'WFH' || nameLower.includes('work from home') || nameLower.includes('remote')) {
                    label = `${name} (WFH)`;
                  } else {
                    label = `${name} (Full Day)`;
                  }
                }
                dynamicOptions.push({
                  label,
                  value: name,
                  unitType: 'full_day'
                });
              }
            }

            // Ensure Half Day Leave is available if not defined in master data
            if (!hasHalfDay && !dynamicOptions.some(o => o.value === 'Half Day' || o.value.toLowerCase().includes('half'))) {
              dynamicOptions.push({
                label: 'Half Day Leave',
                value: 'Half Day',
                unitType: 'half_day'
              });
            }

            // Ensure Hourly Time Off is available
            if (!dynamicOptions.some(o => o.value === 'Hourly' || o.unitType === 'hourly')) {
              dynamicOptions.push({
                label: 'Hourly Time Off',
                value: 'Hourly',
                unitType: 'hourly'
              });
            }

            this.leaveTypeSelectOptions = dynamicOptions;
            this.filterLeaveTypesForRemote();
            this.cdr.detectChanges();
          }
        },
        error: (err) => {
          console.warn('Failed to load master data leave types for modal:', err);
        }
      })
    );

    // Load yearly leave balances for employee
    this.subscriptions.add(
      this.timeoffService.getMyLeaveBalances().subscribe({
        next: (data) => {
          this.yearlyBalances = (data?.yearlyBalances || []).map((b: any) => ({
            ...b,
            allocated_days: Math.round(Number(b.allocated_days) || 0),
            used_days: Math.round(Number(b.used_days) || 0),
            pending_days: Math.round(Number(b.pending_days) || 0),
            available_days: Math.round(Number(b.available_days) || 0),
            carry_forward_days: Math.round(Number(b.carry_forward_days) || 0)
          }));
          this.updateSelectedLeaveBalance(this.leaveForm.value.leaveType);
        },
        error: (err) => {
          console.warn('Failed to load leave balances for modal:', err);
        }
      })
    );

    // Load employee shift bounds to customize half-day sessions and hours
    this.subscriptions.add(
      this.attendanceService.getTodayAttendanceState().subscribe({
        next: (state) => {
          if (state) {
            this.updateShiftInfo(state);
          }
        },
        error: (err) => {
          console.warn('Failed to load shift info for time off modal:', err);
        }
      })
    );

    // Form value changes handling
    this.subscriptions.add(
      this.leaveForm.get('leaveType')?.valueChanges.subscribe((val) => {
        this.onLeaveTypeChange(val);
      })
    );

    this.subscriptions.add(
      this.leaveForm.get('halfDaySession')?.valueChanges.subscribe(() => {
        this.onHalfDaySessionChange();
      })
    );

    this.subscriptions.add(
      this.leaveForm.get('multipleDays')?.valueChanges.subscribe((multi: boolean) => {
        if (multi) {
          this.leaveForm.get('endDate')?.setValidators([Validators.required]);
        } else {
          this.leaveForm.get('endDate')?.clearValidators();
          this.leaveForm.patchValue({ endDate: this.leaveForm.value.startDate }, { emitEvent: false });
        }
        this.leaveForm.get('endDate')?.updateValueAndValidity();
        this.cdr.detectChanges();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  // Getters for form state
  get selectedLeaveType(): string {
    return this.leaveForm.value.leaveType;
  }

  get isMultipleDays(): boolean {
    return this.leaveForm.value.multipleDays;
  }

  get todayIsoMin(): string {
    return toIsoDateLocal(new Date());
  }

  isHalfDayType(leaveType?: string): boolean {
    if (!leaveType) return false;
    if (leaveType === 'Half Day' || leaveType === 'Half-Day') return true;
    const option = this.leaveTypeSelectOptions.find(o => o.value === leaveType);
    if (option?.unitType === 'half_day') return true;
    return leaveType.toLowerCase().includes('half');
  }

  isHourlyType(leaveType?: string): boolean {
    if (!leaveType) return false;
    if (leaveType === 'Hourly') return true;
    const option = this.leaveTypeSelectOptions.find(o => o.value === leaveType);
    if (option?.unitType === 'hourly') return true;
    return leaveType.toLowerCase().includes('hourly');
  }

  isFullDayType(leaveType?: string): boolean {
    if (!leaveType) return false;
    return !this.isHalfDayType(leaveType) && !this.isHourlyType(leaveType);
  }

  get startTimeOptions(): TimeSlotOption[] {
    return filterSlotsNotBeforeNow(this.allTimeSlots, this.leaveForm.value.startDate);
  }

  get endTimeOptions(): TimeSlotOption[] {
    if (!this.isHourlyType(this.selectedLeaveType)) {
      return [];
    }
    const startMin = parseTimeToMinutes(this.leaveForm.value.startTime);
    const startOptions = this.startTimeOptions;
    return startOptions.filter((option) => {
      const optionMinutes = parseTimeToMinutes(option.value);
      return optionMinutes !== null && startMin !== null && optionMinutes > startMin;
    });
  }

  get startTimeSelectOptions(): { label: string; value: string }[] {
    return this.startTimeOptions.map(s => ({ label: s.label, value: s.value }));
  }

  get endTimeSelectOptions(): { label: string; value: string }[] {
    return this.endTimeOptions.map(s => ({ label: s.label, value: s.value }));
  }

  get requestedHours(): number {
    const leaveType = this.leaveForm.value.leaveType;
    if (this.isFullDayType(leaveType)) {
      return this.fullDayDurationHours;
    }
    if (this.isHalfDayType(leaveType)) {
      return this.halfDayDurationHours;
    }
    return hoursBetweenSameDay(this.leaveForm.value.startTime, this.leaveForm.value.endTime);
  }

  resetEndDate(): void {
    this.leaveForm.patchValue({ endDate: this.leaveForm.value.startDate });
  }

  formatTime12to24(time12?: string | null): string {
    if (!time12) return '';
    const parts = time12.match(/(\d+):(\d+)\s*(AM|PM)/i);
    if (!parts) return time12.substring(0, 5);
    let h = parseInt(parts[1], 10);
    const m = parts[2];
    if (parts[3].toUpperCase() === 'PM' && h < 12) h += 12;
    if (parts[3].toUpperCase() === 'AM' && h === 12) h = 0;
    return `${h.toString().padStart(2, '0')}:${m}`;
  }

  private updateShiftInfo(state: TodayAttendanceState): void {
    const start24 = state.shiftStart24 || this.formatTime12to24(state.shiftStart) || '09:00';
    const end24 = state.shiftEnd24 || this.formatTime12to24(state.shiftEnd) || '18:00';
    const lunchStart24 = state.lunchStart24 || this.formatTime12to24(state.lunchStart) || '13:00';
    const lunchEnd24 = state.lunchEnd24 || this.formatTime12to24(state.lunchEnd) || '14:00';

    this.shiftStart24 = start24;
    this.shiftEnd24 = end24;
    this.firstHalfStart24 = start24;
    this.firstHalfEnd24 = lunchStart24;
    this.secondHalfStart24 = lunchEnd24;
    this.secondHalfEnd24 = end24;

    this.isRemoteEmployee = !!state.isRemoteWorker || (state.workMode || '').toLowerCase() === 'remote' || (state.workLocationName || '').toLowerCase().includes('remote');
    this.filterLeaveTypesForRemote();

    if (state.halfDayHours && state.halfDayHours > 0) {
      this.halfDayDurationHours = state.halfDayHours;
    } else {
      const fullDur = hoursBetweenSameDay(start24, end24);
      this.halfDayDurationHours = fullDur > 0 ? fullDur / 2.0 : 4.0;
    }

    const calculatedFullHours = hoursBetweenSameDay(start24, end24);
    if (calculatedFullHours > 0) {
      this.fullDayDurationHours = calculatedFullHours;
    }

    const firstHalfLabel = `First Half (${state.shiftStart || '09:00 AM'} - ${state.lunchStart || '01:00 PM'})`;
    const secondHalfLabel = `Second Half (${state.lunchEnd || '02:00 PM'} - ${state.shiftEnd || '06:00 PM'})`;

    this.halfDaySessionSelectOptions = [
      { label: firstHalfLabel, value: 'First Half' },
      { label: secondHalfLabel, value: 'Second Half' }
    ];

    // Synchronize form controls if already in Half Day or Full Day mode
    const currentLeaveType = this.leaveForm.value.leaveType;
    if (this.isHalfDayType(currentLeaveType)) {
      this.onHalfDaySessionChange();
    } else if (this.isFullDayType(currentLeaveType)) {
      this.leaveForm.patchValue({
        startTime: this.shiftStart24,
        endTime: this.shiftEnd24
      }, { emitEvent: false });
    }
    this.cdr.detectChanges();
  }

  isWfhType(leaveType?: string): boolean {
    if (!leaveType) return false;
    const ltLower = leaveType.toLowerCase();
    return ltLower.includes('wfh') || ltLower.includes('work from home') || ltLower.includes('remote');
  }

  filterLeaveTypesForRemote(): void {
    if (this.isRemoteEmployee) {
      this.leaveTypeSelectOptions = this.leaveTypeSelectOptions.filter(opt => !this.isWfhType(opt.value) && !this.isWfhType(opt.label));
      if (this.isWfhType(this.leaveForm.value.leaveType)) {
        this.leaveForm.patchValue({ leaveType: 'Casual Leave' });
      }
    }
  }

  updateSelectedLeaveBalance(leaveType: string): void {
    this.isWfhSelected = this.isWfhType(leaveType);
    if (!this.yearlyBalances || this.yearlyBalances.length === 0) {
      this.selectedLeaveBalance = null;
      return;
    }
    const ltLower = (leaveType || '').toLowerCase().trim();
    this.selectedLeaveBalance = this.yearlyBalances.find(b => {
      const bName = (b.name || '').toLowerCase().trim();
      const bCode = (b.code || '').toLowerCase().trim();
      return bName === ltLower || bCode === ltLower || ltLower.includes(bName) || bName.includes(ltLower);
    }) || null;
    this.cdr.detectChanges();
  }

  private onLeaveTypeChange(leaveType: string): void {
    this.updateSelectedLeaveBalance(leaveType);
    if (this.isFullDayType(leaveType)) {
      this.leaveForm.patchValue({
        startTime: this.shiftStart24,
        endTime: this.shiftEnd24
      }, { emitEvent: false });
    } else if (this.isHalfDayType(leaveType)) {
      const session = this.leaveForm.value.halfDaySession || 'First Half';
      this.leaveForm.patchValue({
        halfDaySession: session,
        startTime: session === 'Second Half' ? this.secondHalfStart24 : this.firstHalfStart24,
        endTime: session === 'Second Half' ? this.secondHalfEnd24 : this.firstHalfEnd24
      }, { emitEvent: false });
    } else {
      this.leaveForm.patchValue({
        startTime: this.shiftStart24 || '09:00',
        endTime: '10:00'
      }, { emitEvent: false });
    }
    this.cdr.detectChanges();
  }

  private onHalfDaySessionChange(): void {
    const session = this.leaveForm.value.halfDaySession;
    if (session === 'Second Half') {
      this.leaveForm.patchValue({
        startTime: this.secondHalfStart24,
        endTime: this.secondHalfEnd24
      }, { emitEvent: false });
    } else {
      this.leaveForm.patchValue({
        startTime: this.firstHalfStart24,
        endTime: this.firstHalfEnd24
      }, { emitEvent: false });
    }
    this.cdr.detectChanges();
  }

  onStartTimeChange(): void {
    const endOptions = this.endTimeOptions;
    if (endOptions.length && !endOptions.some((option) => option.value === this.leaveForm.value.endTime)) {
      this.leaveForm.patchValue({ endTime: endOptions[0].value });
    }
  }

  // File drag & drop / uploader handlers
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.processFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.processFile(input.files[0]);
    }
  }

  private processFile(file: File): void {
    const allowed = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!allowed.includes(file.type)) {
      this.errorMessage = 'Unsupported format. Please upload PDF, PNG or JPG.';
      return;
    }
    this.errorMessage = '';
    this.uploadedFileName = file.name;
    this.uploadedFileSize = (file.size / 1024 / 1024).toFixed(2) + ' MB';
    this.uploadProgress = 0;
    
    const interval = setInterval(() => {
      this.uploadProgress += 25;
      if (this.uploadProgress >= 100) {
        clearInterval(interval);
      }
      this.cdr.detectChanges();
    }, 100);
  }

  removeUploadedFile(): void {
    this.uploadedFileName = '';
    this.uploadedFileSize = '';
    this.uploadProgress = 0;
  }

  closeModal(): void {
    this.closed.emit(false);
  }

  onOverlayClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.closeModal();
    }
  }

  submitLeaveRequest(): void {
    this.successMessage = '';
    this.errorMessage = '';

    if (this.leaveForm.invalid) {
      this.leaveForm.markAllAsTouched();
      this.toastService.showWarning('Please fill in all required fields marked with *');
      return;
    }

    const { leaveType, startDate, multipleDays, endDate, startTime, endTime, reason } = this.leaveForm.value;

    const startDt = new Date(startDate);
    const endDt = new Date(multipleDays ? endDate : startDate);

    if (multipleDays && endDt < startDt) {
      const msg = 'End date cannot be prior to start date.';
      this.errorMessage = msg;
      this.toastService.showError(msg);
      return;
    }

    if (!multipleDays && startDt.getDay() === 0) {
      const msg = 'Time off cannot be requested on a weekly off day (Sunday).';
      this.errorMessage = msg;
      this.toastService.showError(msg);
      return;
    }

    const datesToSubmit: string[] = [];
    const temp = new Date(startDt.getTime());
    while (temp <= endDt) {
      if (temp.getDay() !== 0) {
        datesToSubmit.push(toIsoDateLocal(temp));
      }
      temp.setDate(temp.getDate() + 1);
    }

    if (datesToSubmit.length === 0) {
      const msg = 'Selected date range only contains Sunday (Weekly Off). No request was submitted.';
      this.errorMessage = msg;
      this.toastService.showError(msg);
      return;
    }

    if (this.isWfhType(leaveType) && this.isRemoteEmployee) {
      const msg = 'Remote employees cannot apply for Work From Home (WFH).';
      this.errorMessage = msg;
      this.toastService.showError(msg);
      return;
    }

    const isFullDay = this.isFullDayType(leaveType);
    const isHalfDay = this.isHalfDayType(leaveType);

    if (this.selectedLeaveBalance) {
      const requestedDays = isHalfDay ? 0.5 : (isFullDay ? datesToSubmit.length : Math.round((this.requestedHours / this.fullDayDurationHours) * 10) / 10);
      if (requestedDays > (this.selectedLeaveBalance.available_days + 1e-4)) {
        const msg = `Insufficient ${this.selectedLeaveBalance.name} balance. You requested ${requestedDays} days, but only ${this.selectedLeaveBalance.available_days} days are available.`;
        this.errorMessage = msg;
        this.toastService.showError(msg);
        return;
      }
    }

    this.isSubmitting = true;

    let backendLeaveType = leaveType;
    if (leaveType === 'Full Day') {
      backendLeaveType = 'Full-Day';
    } else if (leaveType === 'Half Day') {
      backendLeaveType = 'Half-Day';
    } else if (leaveType === 'Hourly') {
      backendLeaveType = 'Hourly';
    }

    let startTimeBackend: string | null = startTime;
    let endTimeBackend: string | null = endTime;

    if (isFullDay) {
      startTimeBackend = null;
      endTimeBackend = null;
    } else if (isHalfDay) {
      const session = this.leaveForm.value.halfDaySession || 'First Half';
      if (session === 'Second Half') {
        startTimeBackend = this.secondHalfStart24;
        endTimeBackend = this.secondHalfEnd24;
      } else {
        startTimeBackend = this.firstHalfStart24;
        endTimeBackend = this.firstHalfEnd24;
      }
    }

    const durationBackend = this.requestedHours;

    let requestObs$;
    if (datesToSubmit.length === 1) {
      requestObs$ = this.timeoffService.requestTimeOff(
        datesToSubmit[0],
        backendLeaveType,
        startTimeBackend,
        endTimeBackend,
        durationBackend,
        reason,
        this.uploadedFileName
      );
    } else {
      requestObs$ = this.timeoffService.requestTimeOffBatch(
        datesToSubmit,
        backendLeaveType,
        startTimeBackend,
        endTimeBackend,
        durationBackend,
        reason,
        this.uploadedFileName
      );
    }

    this.subscriptions.add(
      requestObs$
        .pipe(
          finalize(() => {
            this.isSubmitting = false;
            this.cdr.detectChanges();
          })
        )
        .subscribe({
          next: () => {
            const count = datesToSubmit.length;
            const successMsg = count === 1
              ? 'Time-off request submitted successfully.'
              : `Time-off request for ${count} days submitted successfully.`;
            this.toastService.showSuccess(successMsg);
            this.leaveForm.reset();
            this.removeUploadedFile();
            this.closed.emit(true);
          },
          error: (err) => {
            console.error('Submit Time Off Error:', err);
            const errorMsg = err.error?.detail || 'Failed to submit time-off request. Please try again.';
            this.errorMessage = errorMsg;
            this.toastService.showError(errorMsg);
          }
        })
    );
  }
}
