import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RegularizationService } from '../../../../core/services/regularization.service';
import { RegularizationRequestItem } from '../../../../core/models/regularization.model';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-employee-regularization',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CustomSelectComponent],
  templateUrl: './regularization.html',
  styleUrl: './regularization.css'
})
export class RegularizationComponent implements OnInit {
  regularizationForm: FormGroup;
  requests: RegularizationRequestItem[] = [];
  filteredRequests: RegularizationRequestItem[] = [];
  activeTab: 'all' | 'pending' | 'approved' | 'rejected' = 'all';

  // State flags
  isSubmitting = false;
  successMessage = '';
  errorMessage = '';

  // Dropdown options
  reasonTypeOptions: SelectOption[] = [
    { label: 'Select Reason Type', value: '' },
    { label: 'Missed Punch In/Out', value: 'missed_punch' },
    { label: 'Forgot Punch In', value: 'forgot_punch_in' },
    { label: 'Forgot Punch Out', value: 'forgot_punch_out' },
    { label: 'Late Arrival Sync', value: 'late_sync' },
    { label: 'System/Network Issue', value: 'system_issue' },
    { label: 'Other', value: 'other' }
  ];

  // Pagination
  currentPage = 1;
  pageSize = 5;

  constructor(
    private readonly fb: FormBuilder,
    private readonly regularizationService: RegularizationService,
    private readonly cdr: ChangeDetectorRef
  ) {
    const today = new Date().toISOString().split('T')[0];
    this.regularizationForm = this.fb.group({
      attendanceDate: [today, [Validators.required]],
      requestedPunchIn: [''],
      requestedPunchOut: [''],
      reasonType: ['', [Validators.required]],
      reasonText: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(500)]]
    });
  }

  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests(): void {
    this.regularizationService.getMyRequests(1, 1000).subscribe({
      next: (res) => {
        this.requests = res.items || [];
        this.applyTabFilter();
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading regularization requests', err);
        this.errorMessage = 'Failed to load regularization history.';
        this.cdr.detectChanges();
      }
    });
  }

  setTab(tab: 'all' | 'pending' | 'approved' | 'rejected'): void {
    this.activeTab = tab;
    this.currentPage = 1;
    this.applyTabFilter();
  }

  applyTabFilter(): void {
    if (this.activeTab === 'all') {
      this.filteredRequests = this.requests;
    } else {
      this.filteredRequests = this.requests.filter(
        (req) => req.status.toLowerCase() === this.activeTab
      );
    }
  }

  // Getters for pagination
  get pagedRequests(): RegularizationRequestItem[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    return this.filteredRequests.slice(startIndex, startIndex + this.pageSize);
  }

  get endIndex(): number {
    return Math.min(this.currentPage * this.pageSize, this.filteredRequests.length);
  }

  get totalPages(): number {
    return Math.ceil(this.filteredRequests.length / this.pageSize);
  }

  private _cachedTotalPages = 0;
  private _cachedPageNumbers: number[] = [];

  get pageNumbers(): number[] {
    const pages = this.totalPages;
    if (pages !== this._cachedTotalPages) {
      this._cachedTotalPages = pages;
      this._cachedPageNumbers = Array.from({ length: pages }, (_, i) => i + 1);
    }
    return this._cachedPageNumbers;
  }

  setPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  onSubmit(): void {
    if (this.regularizationForm.invalid) {
      this.regularizationForm.markAllAsTouched();
      return;
    }

    const formVal = this.regularizationForm.value;
    
    // Validate that at least one requested punch time is provided
    if (!formVal.requestedPunchIn && !formVal.requestedPunchOut) {
      this.errorMessage = 'Please provide at least a requested punch-in or punch-out time.';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    const payload = {
      attendanceDate: formVal.attendanceDate,
      requestedPunchIn: formVal.requestedPunchIn || null,
      requestedPunchOut: formVal.requestedPunchOut || null,
      reasonType: formVal.reasonType,
      reasonText: formVal.reasonText
    };

    this.regularizationService.submitRegularization(payload).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.successMessage = 'Regularization request submitted successfully!';
        
        // Reset Form
        const today = new Date().toISOString().split('T')[0];
        this.regularizationForm.reset({
          attendanceDate: today,
          requestedPunchIn: '',
          requestedPunchOut: '',
          reasonType: '',
          reasonText: ''
        });

        this.loadRequests();
        
        // Clear success message after 5 seconds
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 5000);
      },
      error: (err) => {
        this.isSubmitting = false;
        const detail = err?.error?.detail;
        this.errorMessage = typeof detail === 'string' ? detail : 'Unable to submit regularization request.';
        this.cdr.detectChanges();
      }
    });
  }

  getReasonTypeLabel(type: string): string {
    const option = this.reasonTypeOptions.find(opt => opt.value === type);
    return option ? option.label : type;
  }

  formatTime(timeStr?: string | null): string {
    if (!timeStr) return '-';
    // If has seconds or milliseconds, format it to HH:MM
    const parts = timeStr.split(':');
    if (parts.length >= 2) {
      return `${parts[0]}:${parts[1]}`;
    }
    return timeStr;
  }
}
