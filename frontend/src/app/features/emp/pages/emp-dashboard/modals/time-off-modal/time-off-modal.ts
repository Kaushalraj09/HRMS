import { Component, OnInit, OnDestroy, EventEmitter, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { forkJoin, Subscription } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { AttendanceService } from '../../../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../../../core/services/timeoff.service';
import {
  TimeSlotOption,
  buildHalfHourSlots,
  filterSlotsNotBeforeNow,
  hoursBetweenSameDay,
  parseTimeToMinutes,
  toIsoDateLocal
} from '../../../../../../core/utils/timeoff-time.util';

@Component({
  selector: 'app-time-off-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
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

  readonly allTimeSlots: TimeSlotOption[] = buildHalfHourSlots();

  private subscriptions = new Subscription();

  constructor(
    private readonly fb: FormBuilder,
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly cdr: ChangeDetectorRef
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

  get requestedHours(): number {
    const leaveType = this.leaveForm.value.leaveType;
    if (leaveType === 'Full Day') {
      return 9.0;
    }
    if (leaveType === 'Half Day') {
      return 4.0;
    }
    return hoursBetweenSameDay(this.leaveForm.value.startTime, this.leaveForm.value.endTime);
  }

  resetEndDate(): void {
    this.leaveForm.patchValue({ endDate: this.leaveForm.value.startDate });
  }

  private onLeaveTypeChange(leaveType: string): void {
    if (leaveType === 'Full Day') {
      this.leaveForm.patchValue({
        startTime: '09:00',
        endTime: '18:00'
      }, { emitEvent: false });
    } else if (leaveType === 'Half Day') {
      this.leaveForm.patchValue({
        halfDaySession: 'First Half',
        startTime: '09:00',
        endTime: '13:00'
      }, { emitEvent: false });
    } else {
      this.leaveForm.patchValue({
        startTime: '09:00',
        endTime: '10:00'
      }, { emitEvent: false });
    }
    this.cdr.detectChanges();
  }

  private onHalfDaySessionChange(): void {
    const session = this.leaveForm.value.halfDaySession;
    if (session === 'First Half') {
      this.leaveForm.patchValue({
        startTime: '09:00',
        endTime: '13:00'
      }, { emitEvent: false });
    } else {
      this.leaveForm.patchValue({
        startTime: '14:00',
        endTime: '18:00'
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
      return;
    }

    const { leaveType, startDate, multipleDays, endDate, startTime, endTime, reason } = this.leaveForm.value;

    const startDt = new Date(startDate);
    const endDt = new Date(multipleDays ? endDate : startDate);

    if (multipleDays && endDt < startDt) {
      this.errorMessage = 'End date cannot be prior to start date.';
      return;
    }

    const datesToSubmit: string[] = [];
    const temp = new Date(startDt.getTime());
    while (temp <= endDt) {
      const dayOfWeek = temp.getDay();
      if (dayOfWeek !== 0 && dayOfWeek !== 6) { // Exclude weekends
        datesToSubmit.push(temp.toISOString().split('T')[0]);
      }
      temp.setDate(temp.getDate() + 1);
    }

    if (datesToSubmit.length === 0) {
      this.errorMessage = 'Selected date range only contains weekends. No request was submitted.';
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

    const requests$ = datesToSubmit.map(dStr => 
      this.timeoffService.requestTimeOff(
        dStr,
        backendLeaveType,
        startTimeBackend,
        endTimeBackend,
        durationBackend,
        reason,
        this.uploadedFileName
      )
    );

    this.subscriptions.add(
      forkJoin(requests$)
        .pipe(
          finalize(() => {
            this.isSubmitting = false;
            this.cdr.detectChanges();
          })
        )
        .subscribe({
          next: () => {
            this.successMessage = `Successfully requested ${datesToSubmit.length} working day(s) of time off.`;
            this.leaveForm.reset();
            this.removeUploadedFile();
            setTimeout(() => {
              this.closed.emit(true);
            }, 1800);
          },
          error: (err) => {
            const detail = err?.error?.detail;
            this.errorMessage = typeof detail === 'string' ? detail : 'Failed to submit request. Please try again.';
          }
        })
    );
  }
}
