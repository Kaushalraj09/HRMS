import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { RegularizationService } from '../../../../core/services/regularization.service';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { RegularizationRequestItem } from '../../../../core/models/regularization.model';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-hr-regularization-requests',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  templateUrl: './regularization-requests.html',
  styleUrl: './regularization-requests.css'
})
export class RegularizationRequestsComponent implements OnInit, OnDestroy {
  pendingRequests: RegularizationRequestItem[] = [];
  activeTab: 'pending' | 'history' = 'pending';

  // Filters
  searchTerm = '';
  selectedReasonType = '';

  // Decision Modal State
  selectedRequest: RegularizationRequestItem | null = null;
  decisionComment = '';
  isSavingDecision = false;
  decisionError = '';

  // Options
  reasonTypeOptions: SelectOption[] = [
    { label: 'All Reason Types', value: '' },
    { label: 'Missed Punch In/Out', value: 'missed_punch' },
    { label: 'Forgot Punch In', value: 'forgot_punch_in' },
    { label: 'Forgot Punch Out', value: 'forgot_punch_out' },
    { label: 'Late Arrival Sync', value: 'late_sync' },
    { label: 'System/Network Issue', value: 'system_issue' },
    { label: 'Other', value: 'other' }
  ];

  // Pagination
  currentPage = 1;
  pageSize = 10;
  totalItems = 0;

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly regularizationService: RegularizationService,
    private readonly attendanceService: AttendanceService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadPendingRequests();

    // WebSocket updates
    this.subscriptions.add(
      this.attendanceService.wsMessage$.subscribe((msg) => {
        if (msg.type === 'REGULARIZATION_REQUEST' || msg.type === 'REGULARIZATION_UPDATE') {
          this.loadPendingRequests();
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadPendingRequests();
  }

  loadPendingRequests(): void {
    this.regularizationService.getPendingRequests(
      this.currentPage,
      this.pageSize,
      this.searchTerm,
      this.selectedReasonType
    ).subscribe({
      next: (res: any) => {
        this.pendingRequests = res.items;
        this.totalItems = res.totalItems;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading pending regularizations', err);
      }
    });
  }

  setActiveTab(tab: 'pending' | 'history'): void {
    // Left for potential future tab extensions, but template only renders pending requests.
    this.currentPage = 1;
    this.loadPendingRequests();
  }

  get totalPages(): number {
    return Math.ceil(this.totalItems / this.pageSize);
  }

  get endIndex(): number {
    return Math.min(this.currentPage * this.pageSize, this.totalItems);
  }

  get pageNumbers(): number[] {
    return Array.from({ length: this.totalPages }, (_, i) => i + 1);
  }

  setPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadPendingRequests();
    }
  }

  openDecisionModal(req: RegularizationRequestItem): void {
    this.selectedRequest = req;
    this.decisionComment = '';
    this.decisionError = '';
  }

  closeDecisionModal(): void {
    this.selectedRequest = null;
  }

  submitDecision(status: 'approved' | 'rejected'): void {
    if (!this.selectedRequest) return;

    if (status === 'rejected' && !this.decisionComment.trim()) {
      this.decisionError = 'Comment is required when rejecting a request.';
      return;
    }

    this.isSavingDecision = true;
    this.decisionError = '';
    this.cdr.detectChanges();

    this.regularizationService.submitDecision(this.selectedRequest.id, {
      status,
      reviewComment: this.decisionComment
    }).subscribe({
      next: () => {
        this.isSavingDecision = false;
        this.closeDecisionModal();
        this.loadPendingRequests();
      },
      error: (err) => {
        this.isSavingDecision = false;
        const detail = err?.error?.detail;
        this.decisionError = typeof detail === 'string' ? detail : 'Failed to save decision.';
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
    const parts = timeStr.split(':');
    if (parts.length >= 2) {
      return `${parts[0]}:${parts[1]}`;
    }
    return timeStr;
  }
}
