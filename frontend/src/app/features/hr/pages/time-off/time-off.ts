import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { AuthService } from '../../../../core/services/auth.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-hr-time-off',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent],
  templateUrl: './time-off.html',
  styleUrls: ['./time-off.css']
})
export class HrTimeOffComponent implements OnInit, OnDestroy {
  isAdmin = false;
  pendingRequests: any[] = [];
  processedRequests: any[] = [];
  
  // Search & Filter state
  searchTerm = '';
  selectedLeaveType = '';
  selectedStatus = ''; // For history
  
  // Current tab: 'pending' or 'history'
  activeTab: 'pending' | 'history' = 'pending';
  
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

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    this.isAdmin = user?.role === 'admin';

    this.loadPendingRequests();
    this.loadProcessedRequests();

    // WebSocket updates
    this.subscriptions.add(
      this.timeoffService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
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
        this.pendingRequests = res.items;
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
        this.processedRequests = res.items;
        this.historyTotal = res.totalItems;
        this.cdr.detectChanges();
      }
    });
  }

  processRequest(requestId: number, action: 'APPROVE' | 'REJECT'): void {
    let approvedHours: number | undefined;
    if (action === 'APPROVE') {
      const req = this.pendingRequests.find((r) => r.id === requestId);
      approvedHours = req?.duration_hours;
    }

    this.timeoffService.approveTimeOffRequest(requestId, action, approvedHours).subscribe({
      next: () => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
      },
      error: (err) => {
        alert(err?.error?.detail || `Error performing ${action.toLowerCase()} action.`);
      }
    });
  }

  setActiveTab(tab: 'pending' | 'history'): void {
    this.activeTab = tab;
  }

  get filteredPendingRequests(): any[] {
    return this.pendingRequests;
  }

  get filteredProcessedRequests(): any[] {
    return this.processedRequests;
  }

  selectedRequest: any = null;

  viewRequestDetails(req: any): void {
    this.selectedRequest = req;
  }

  closeDetailsModal(): void {
    this.selectedRequest = null;
  }

  processRequestFromModal(requestId: number, action: 'APPROVE' | 'REJECT'): void {
    this.processRequest(requestId, action);
    this.closeDetailsModal();
  }

  downloadAttachment(fileName: string): void {
    alert(`Downloading attachment: ${fileName}`);
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
