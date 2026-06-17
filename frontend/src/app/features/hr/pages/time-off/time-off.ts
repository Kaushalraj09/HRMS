import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AttendanceService } from '../../../../core/services/attendance.service';
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

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly attendanceService: AttendanceService,
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
      this.attendanceService.timeoffUpdate$.subscribe(() => {
        this.loadPendingRequests();
        this.loadProcessedRequests();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadPendingRequests(): void {
    this.attendanceService.getPendingTimeOffRequests().subscribe({
      next: (requests) => {
        this.pendingRequests = requests;
        this.cdr.detectChanges();
      }
    });
  }

  loadProcessedRequests(): void {
    this.attendanceService.getProcessedTimeOffRequests().subscribe({
      next: (requests) => {
        this.processedRequests = requests;
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

    this.attendanceService.approveTimeOffRequest(requestId, action, approvedHours).subscribe({
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
    return this.pendingRequests.filter((req) => {
      const matchesSearch = this.matchesSearchText(req);
      const matchesType = !this.selectedLeaveType || req.leave_type === this.selectedLeaveType;
      return matchesSearch && matchesType;
    });
  }

  get filteredProcessedRequests(): any[] {
    return this.processedRequests.filter((req) => {
      const matchesSearch = this.matchesSearchText(req);
      const matchesType = !this.selectedLeaveType || req.leave_type === this.selectedLeaveType;
      const matchesStatus = !this.selectedStatus || req.status === this.selectedStatus;
      return matchesSearch && matchesType && matchesStatus;
    });
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
