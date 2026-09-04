import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { groupTimeOffRequests } from '../../../../core/utils/timeoff-grouping.util';
import { GroupedTimeOffRequest } from '../../../../core/models/timeoff.model';

@Component({
  selector: 'app-hr-time-off',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  templateUrl: './time-off.html',
  styleUrls: ['./time-off.css']
})
export class HrTimeOffComponent implements OnInit, OnDestroy {
  isAdmin = false;
  pendingRequests: GroupedTimeOffRequest[] = [];
  processedRequests: GroupedTimeOffRequest[] = [];
  
  // Search & Filter state
  searchTerm = '';
  selectedDepartment = '';
  selectedLeaveType = '';
  selectedStatus = '';
  dateRangeStart = '';
  dateRangeEnd = '';
  
  // Current tab: 'all' | 'pending' | 'approved' | 'rejected'
  activeTab: 'all' | 'pending' | 'approved' | 'rejected' = 'pending';
  
  // Custom Select options
  leaveTypeOptions = [
    { label: 'All Leave Types', value: '' },
    { label: 'Hourly', value: 'Hourly' },
    { label: 'Half Day', value: 'Half-Day' },
    { label: 'Full Day', value: 'Full-Day' }
  ];

  statusOptions = [
    { label: 'All Statuses', value: '' },
    { label: 'Approved', value: 'Approved' },
    { label: 'Rejected', value: 'Rejected' }
  ];

  // Pagination state
  pendingPage = 1;
  historyPage = 1;
  pageSize = 10;
  pendingTotal = 0;
  historyTotal = 0;
  
  // Counts for pills
  allTotal = 0;
  approvedTotal = 0;
  rejectedTotal = 0;

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef,
    private readonly toastService: ToastService
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    this.isAdmin = user?.role === 'admin';

    this.loadPendingRequests();
    this.loadProcessedRequests();
    this.loadCounts();

    // WebSocket updates
    this.subscriptions.add(
      this.timeoffService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
        this.loadCounts();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  onFilterChange(): void {
    this.pendingPage = 1;
    this.historyPage = 1;
    this.loadPendingRequests();
    this.loadProcessedRequests();
    this.loadCounts();
  }

  setPendingPage(page: number): void {
    if (page >= 1 && page <= this.pendingTotalPages) {
      this.pendingPage = page;
      this.loadPendingRequests();
    }
  }

  setHistoryPage(page: number): void {
    if (page >= 1 && page <= this.historyTotalPages) {
      this.historyPage = page;
      this.loadProcessedRequests();
    }
  }

  get pendingTotalPages(): number {
    return Math.ceil(this.pendingTotal / this.pageSize);
  }

  get historyTotalPages(): number {
    return Math.ceil(this.historyTotal / this.pageSize);
  }

  get pendingPageNumbers(): number[] {
    return Array.from({ length: this.pendingTotalPages }, (_, i) => i + 1);
  }

  get historyPageNumbers(): number[] {
    return Array.from({ length: this.historyTotalPages }, (_, i) => i + 1);
  }

  loadPendingRequests(): void {
    this.timeoffService.getPendingTimeOffRequests(
      this.pendingPage,
      this.pageSize,
      this.searchTerm,
      this.selectedLeaveType
    ).subscribe({
      next: (res) => {
        this.pendingRequests = groupTimeOffRequests(res.items);
        this.pendingTotal = res.totalItems;
        this.cdr.detectChanges();
      }
    });
  }

  loadProcessedRequests(): void {
    this.timeoffService.getProcessedTimeOffRequests(
      this.historyPage,
      this.pageSize,
      this.searchTerm,
      this.selectedLeaveType,
      this.selectedStatus
    ).subscribe({
      next: (res) => {
        this.processedRequests = groupTimeOffRequests(res.items);
        this.historyTotal = res.totalItems;
        this.cdr.detectChanges();
      }
    });
  }

  loadCounts(): void {
    this.timeoffService.getTimeOffCounts(
      this.searchTerm,
      this.selectedLeaveType
    ).subscribe({
      next: (counts) => {
        this.allTotal = counts.all;
        this.pendingTotal = counts.pending; // Also updates pendingTotal in case it's useful
        this.approvedTotal = counts.approved;
        this.rejectedTotal = counts.rejected;
        this.cdr.detectChanges();
      }
    });
  }

  formatHours(hours: number): string {
    if (hours === 0 || !hours) return '0h 0m';
    const totalMinutes = Math.round(hours * 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return `${h}h ${m}m`;
  }

  formatDuration(req: GroupedTimeOffRequest): string {
    if (req.leave_type === 'Full-Day' || req.leave_type === 'Full Day') {
      const days = req.requests.length;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    if (req.leave_type === 'Half-Day' || req.leave_type === 'Half Day') {
      const days = req.requests.length * 0.5;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    return this.formatHours(req.totalDurationHours);
  }

  processRequest(batchId: string, action: 'APPROVE' | 'REJECT'): void {
    const reqGroup = this.pendingRequests.find((r) => r.id === batchId) || this.processedRequests.find((r) => r.id === batchId);
    if (!reqGroup) return;

    let processedCount = 0;
    const reqIds = reqGroup.requests.map(r => r.id);

    for (const rId of reqIds) {
      let approvedHours: number | undefined;
      if (action === 'APPROVE') {
        const r = reqGroup.requests.find(x => x.id === rId);
        approvedHours = r?.duration_hours;
      }

      this.timeoffService.approveTimeOffRequest(rId, action, approvedHours).subscribe({
        next: () => {
          processedCount++;
          if (processedCount === reqIds.length) {
            this.toastService.showSuccess(`Request ${action.toLowerCase()}d successfully`);
            this.loadPendingRequests();
            this.loadProcessedRequests();
            this.loadCounts();
          }
        },
        error: (err) => {
          if (processedCount === 0) { // Only alert on first error
            this.toastService.showError(err?.error?.detail || `Error performing ${action.toLowerCase()} action.`);
          }
        }
      });
    }
  }

  setActiveTab(tab: 'all' | 'pending' | 'approved' | 'rejected'): void {
    this.activeTab = tab;
    if (tab === 'pending') {
      this.pendingPage = 1;
      this.loadPendingRequests();
    } else {
      this.historyPage = 1;
      if (tab === 'approved') {
        this.selectedStatus = 'Approved';
      } else if (tab === 'rejected') {
        this.selectedStatus = 'Rejected';
      } else {
        this.selectedStatus = '';
      }
      this.loadProcessedRequests();
    }
  }

  get filteredPendingRequests(): any[] {
    return this.pendingRequests;
  }

  get filteredProcessedRequests(): any[] {
    return this.processedRequests;
  }

  selectedRequest: GroupedTimeOffRequest | null = null;

  viewRequestDetails(req: GroupedTimeOffRequest): void {
    this.selectedRequest = req;
  }

  closeDetailsModal(): void {
    this.selectedRequest = null;
  }

  processRequestFromModal(batchId: string, action: 'APPROVE' | 'REJECT'): void {
    this.processRequest(batchId, action);
    this.closeDetailsModal();
  }

  downloadAttachment(fileName: string): void {
    this.toastService.showInfo(`Downloading attachment: ${fileName}`);
  }

  private matchesSearchText(req: any): boolean {
    const query = this.searchTerm.trim().toLowerCase();
    if (!query) {
      return true;
    }
    const name = (req.employee_name || '').toLowerCase();
    const code = (req.employee_code || '').toLowerCase();
    return name.includes(query) || code.includes(query);
  }
}
