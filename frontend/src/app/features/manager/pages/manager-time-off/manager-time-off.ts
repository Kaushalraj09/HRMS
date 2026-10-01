import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ManagerService } from '../../../../core/services/manager.service';
import { ToastService } from '../../../../core/services/toast.service';
import { TimeOffRequest } from '../../../../core/models/timeoff.model';

@Component({
  selector: 'app-manager-time-off',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './manager-time-off.html',
  styleUrls: ['./manager-time-off.css']
})
export class ManagerTimeOffComponent implements OnInit {
  activeTab: 'pending' | 'history' = 'pending';

  pendingRequests: TimeOffRequest[] = [];
  historyRequests: TimeOffRequest[] = [];
  isLoading = true;

  // Pagination for pending
  pendingPage = 1;
  pendingPageSize = 10;
  pendingTotal = 0;
  pendingTotalPages = 1;

  // Pagination for history
  historyPage = 1;
  historyPageSize = 10;
  historyTotal = 0;
  historyTotalPages = 1;

  // Decision Modal
  isDecisionModalOpen = false;
  selectedRequest: TimeOffRequest | null = null;
  decisionType: 'approve' | 'reject' = 'approve';
  decisionComment = '';
  isProcessing = false;

  constructor(
    private readonly managerService: ManagerService,
    private readonly toastService: ToastService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading = true;
    if (this.activeTab === 'pending') {
      this.managerService
        .getTeamLeaveRequests(this.pendingPage, this.pendingPageSize, 'pending')
        .subscribe({
          next: res => {
            this.pendingRequests = res.items || [];
            this.pendingTotal = res.totalItems;
            this.pendingTotalPages = res.totalPages || 1;
            this.isLoading = false;
            this.cdr.markForCheck();
          },
          error: err => {
            this.isLoading = false;
            this.toastService.showError(err?.error?.detail || 'Failed to load pending requests');
            this.cdr.markForCheck();
          }
        });
    } else {
      this.managerService
        .getTeamLeaveRequests(this.historyPage, this.historyPageSize, 'processed')
        .subscribe({
          next: res => {
            this.historyRequests = res.items || [];
            this.historyTotal = res.totalItems;
            this.historyTotalPages = res.totalPages || 1;
            this.isLoading = false;
            this.cdr.markForCheck();
          },
          error: err => {
            this.isLoading = false;
            this.toastService.showError(err?.error?.detail || 'Failed to load request history');
            this.cdr.markForCheck();
          }
        });
    }
  }

  switchTab(tab: 'pending' | 'history'): void {
    if (this.activeTab !== tab) {
      this.activeTab = tab;
      this.loadData();
    }
  }

  openDecisionModal(req: TimeOffRequest, type: 'approve' | 'reject'): void {
    this.selectedRequest = req;
    this.decisionType = type;
    this.decisionComment = '';
    this.isDecisionModalOpen = true;
  }

  closeDecisionModal(): void {
    this.isDecisionModalOpen = false;
    this.selectedRequest = null;
    this.decisionComment = '';
  }

  submitDecision(): void {
    if (!this.selectedRequest) return;
    if (this.decisionType === 'reject' && !this.decisionComment.trim()) {
      this.toastService.showError('Please provide a reason for rejecting the leave request.');
      return;
    }

    this.isProcessing = true;
    this.cdr.markForCheck();
    const reqId = this.selectedRequest.id;

    if (this.decisionType === 'approve') {
      this.managerService.approveLeaveRequest(reqId, this.decisionComment).subscribe({
        next: () => {
          this.isProcessing = false;
          this.toastService.showSuccess('Leave request approved and forwarded to HR for final review.');
          this.closeDecisionModal();
          this.loadData();
          this.cdr.markForCheck();
        },
        error: err => {
          this.isProcessing = false;
          this.toastService.showError(err?.error?.detail || 'Failed to approve request');
          this.cdr.markForCheck();
        }
      });
    } else {
      this.managerService.rejectLeaveRequest(reqId, this.decisionComment).subscribe({
        next: () => {
          this.isProcessing = false;
          this.toastService.showInfo('Leave request rejected.');
          this.closeDecisionModal();
          this.loadData();
          this.cdr.markForCheck();
        },
        error: err => {
          this.isProcessing = false;
          this.toastService.showError(err?.error?.detail || 'Failed to reject request');
          this.cdr.markForCheck();
        }
      });
    }
  }

  goToPendingPage(page: number): void {
    if (page >= 1 && page <= this.pendingTotalPages) {
      this.pendingPage = page;
      this.loadData();
    }
  }

  goToHistoryPage(page: number): void {
    if (page >= 1 && page <= this.historyTotalPages) {
      this.historyPage = page;
      this.loadData();
    }
  }
}
