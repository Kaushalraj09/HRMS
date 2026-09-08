import { Component, OnInit, OnDestroy, EventEmitter, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { AttendanceService } from '../../../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../../../core/services/timeoff.service';
import { TodayAttendanceState } from '../../../../../../core/models/attendance.model';
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

  readonly leaveTypeSelectOptions = [
    { label: 'Hourly Time Off', value: 'Hourly' },
    { label: 'Full Day Leave', value: 'Full Day' },
    { label: 'Half Day Leave', value: 'Half Day' }
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
    private readonly toastService: ToastService
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

  get startTimeOptions(): TimeSlotOption[] {
    return filterSlotsNotBeforeNow(this.allTimeSlots, this.leaveForm.value.startDate);
  }

  get endTimeOptions(): TimeSlotOption[] {
    if (this.selectedLeaveType !== 'Hourly') {
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
    if (leaveType === 'Full Day') {
      return this.fullDayDurationHours;
    }
    if (leaveType === 'Half Day') {
      return this.halfDayDurationHours;
    }
    return hoursBetweenSameDay(this.leaveForm.value.startTime, this.leaveForm.value.endTime);
  }

  resetEndDate(): void {
    this.leaveForm.patchValue({ endDate: this.leaveForm.value.startDate });
  }

  private updateShiftInfo(state: TodayAttendanceState): void {
    if (state.shiftStart24) {
      this.shiftStart24 = state.shiftStart24;
    }
    if (state.shiftEnd24) {
      this.shiftEnd24 = state.shiftEnd24;
    }
    if (state.lunchStart24) {
      this.firstHalfEnd24 = state.lunchStart24;
    }
    if (state.lunchEnd24) {
      this.secondHalfStart24 = state.lunchEnd24;
    }
    this.firstHalfStart24 = this.shiftStart24;
    this.secondHalfEnd24 = this.shiftEnd24;

    if (state.halfDayHours && state.halfDayHours > 0) {
      this.halfDayDurationHours = state.halfDayHours;
    }

    const calculatedFullHours = hoursBetweenSameDay(this.shiftStart24, this.shiftEnd24);
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
    if (currentLeaveType === 'Half Day') {
      this.onHalfDaySessionChange();
    } else if (currentLeaveType === 'Full Day') {
      this.leaveForm.patchValue({
        startTime: this.shiftStart24,
        endTime: this.shiftEnd24
      }, { emitEvent: false });
    }
    this.cdr.detectChanges();
  }

  private onLeaveTypeChange(leaveType: string): void {
    if (leaveType === 'Full Day') {
      this.leaveForm.patchValue({
        startTime: this.shiftStart24,
        endTime: this.shiftEnd24
      }, { emitEvent: false });
    } else if (leaveType === 'Half Day') {
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

    this.isSubmitting = true;

    const backendLeaveType = leaveType === 'Full Day' ? 'Full-Day' : (leaveType === 'Half Day' ? 'Half-Day' : 'Hourly');
    let startTimeBackend: string | null = startTime;
    let endTimeBackend: string | null = endTime;

    if (leaveType === 'Full Day') {
      startTimeBackend = null;
      endTimeBackend = null;
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
