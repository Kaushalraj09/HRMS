import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { TimeoffService } from '../../../../core/services/timeoff.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TimeOffModalComponent } from '../emp-dashboard/modals/time-off-modal/time-off-modal';
import { TimeEngineService } from '../../../../core/services/time-engine.service';
import { ToastService } from '../../../../core/services/toast.service';
import { groupTimeOffRequests } from '../../../../core/utils/timeoff-grouping.util';
import { GroupedTimeOffRequest } from '../../../../core/models/timeoff.model';

@Component({
  selector: 'app-emp-time-off',
  standalone: true,
  imports: [CommonModule, FormsModule, TimeOffModalComponent],
  templateUrl: './time-off.html',
  styleUrls: ['./time-off.css']
})
export class EmpTimeOffComponent implements OnInit, OnDestroy {
  requests: GroupedTimeOffRequest[] = [];
  
  // Balance metrics
  approvedHours = 0;
  remainingHours = 9.0;
  requestedHours = 0;

  leaveYear = new Date().getFullYear();
  paidLeave = { allocated: 18, used: 0, pending: 0, remaining: 18 };
  unpaidLeave = { allocated: 12, used: 0, pending: 0, remaining: 12 };
  yearlyBalances: any[] = [];

  selectedRequest: GroupedTimeOffRequest | null = null;
  showRequestModal = false;
  isCancelling = false;

  formatHours(hours: number): string {
    if (hours === 0 || !hours) return '0h 0m';
    const totalMinutes = Math.round(hours * 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return `${h}h ${m}m`;
  }

  formatDuration(req: GroupedTimeOffRequest): string {
    const lt = (req.leave_type || '').toLowerCase();
    const isHalf = lt === 'half-day' || lt === 'half day' || lt.includes('half');
    const isFull = lt === 'full-day' || lt === 'full day' || lt.includes('casual') || lt.includes('sick') || lt.includes('earned') || lt.includes('privilege') || lt.includes('comp') || lt.includes('wfh') || lt.includes('home') || lt.includes('remote');

    if (isFull) {
      const days = req.requests.length;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    if (isHalf) {
      const days = req.requests.length * 0.5;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    if (req.totalDurationHours >= 8 && req.totalDurationHours % 8 === 0) {
      const days = req.totalDurationHours / 8;
      return `${days} Day${days > 1 ? 's' : ''}`;
    }
    return this.formatHours(req.totalDurationHours);
  }

  formatTimeSlot(startTime?: string | null, endTime?: string | null, leaveType?: string | null): string {
    const lt = (leaveType || '').toLowerCase();
    const isFull = !startTime || lt === 'full-day' || lt === 'full day' || lt.includes('casual') || lt.includes('sick') || lt.includes('earned') || lt.includes('privilege') || lt.includes('comp') || lt.includes('wfh') || lt.includes('home') || lt.includes('remote');

    if (isFull) {
      return 'Full Day';
    }
    const formatTime = (t: string) => {
      if (!t) return '';
      const parts = t.trim().split(':');
      if (parts.length >= 2) {
        let hour = parseInt(parts[0], 10);
        const min = parts[1];
        const ampm = hour >= 12 ? 'PM' : 'AM';
        hour = hour % 12 || 12;
        const hourStr = hour < 10 ? `0${hour}` : `${hour}`;
        return `${hourStr}:${min} ${ampm}`;
      }
      return t;
    };
    if (endTime) {
      return `${formatTime(startTime)} – ${formatTime(endTime)}`;
    }
    return formatTime(startTime);
  }

  // Pagination state
  page = 1;
  pageSize = 10;
  totalItems = 0;

  showTimeOffModal = false;

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly attendanceService: AttendanceService,
    private readonly timeoffService: TimeoffService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef,
    private readonly timeEngine: TimeEngineService,
    private readonly toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadRequests();
    this.loadBalances();

    this.subscriptions.add(
      this.timeEngine.state$.subscribe((state) => {
        if (state) {
          this.approvedHours = (state.approvedSeconds || 0) / 3600;
          this.remainingHours = (state.remainingSeconds || 0) / 3600;
          this.cdr.detectChanges();
        }
      })
    );

    // WebSocket updates
    this.subscriptions.add(
      this.timeoffService.timeoffUpdate$.subscribe(() => {
        this.loadRequests();
        this.loadBalances();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadRequests(): void {
    this.timeoffService.getMyTimeOffRequests(this.page, this.pageSize).subscribe({
      next: (res) => {
        this.requests = groupTimeOffRequests(res.items);
        this.totalItems = res.totalItems; // Pagination might be weird if backend returns 10 items but they group to 3. But it's fine for now as per instructions.
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading time off requests', err);
        this.toastService.showError('Failed to load time-off requests.');
      }
    });
  }

  loadBalances(): void {
    this.attendanceService.getTodayAttendanceState().subscribe({
      next: (state) => {
        this.timeEngine.updateState(state);
      }
    });

    this.timeoffService.getMyLeaveBalances().subscribe({
      next: (res) => {
        if (res) {
          this.leaveYear = res.leave_year || new Date().getFullYear();
          if (res.paid_leave) {
            this.paidLeave = res.paid_leave;
          }
          if (res.unpaid_leave) {
            this.unpaidLeave = res.unpaid_leave;
          }
          if (res.yearlyBalances) {
            this.yearlyBalances = res.yearlyBalances;
          }
          this.cdr.detectChanges();
        }
      },
      error: (err) => console.warn('Could not load yearly balances', err)
    });

    this.timeoffService.getMyTimeOffRequests(1, 1000).subscribe({
      next: (res) => {
        let requested = 0;
        for (const req of res.items) {
          if (req.status === 'Pending') {
            requested += req.duration_hours;
          }
        }
        this.requestedHours = requested;
        this.cdr.detectChanges();
      }
    });
  }

  setPage(p: number): void {
    if (p >= 1 && p <= this.totalPages) {
      this.page = p;
      this.loadRequests();
    }
  }

  get totalPages(): number {
    return Math.ceil(this.totalItems / this.pageSize);
  }

  get pageNumbers(): number[] {
    return Array.from({ length: this.totalPages }, (_, i) => i + 1);
  }

  openTimeOffModal(): void {
    this.showTimeOffModal = true;
    this.cdr.detectChanges();
  }

  onTimeOffModalClose(refresh: boolean): void {
    this.showTimeOffModal = false;
    if (refresh) {
      this.loadRequests();
      this.loadBalances();
    }
    this.cdr.detectChanges();
  }

  closeRequestModal(): void {
    this.showRequestModal = false;
  }

  viewRequestDetails(req: GroupedTimeOffRequest): void {
    this.selectedRequest = req;
  }

  closeDetailsModal(): void {
    this.selectedRequest = null;
  }

  cancelRequest(id: string): void {
    if (confirm('Are you sure you want to cancel this time-off request?')) {
      this.isCancelling = true;
      
      const reqIds = this.selectedRequest?.requests.map((r: any) => r.id) || [];
      if (reqIds.length === 0) return;

      let canceledCount = 0;
      let hasError = false;
      for (const rId of reqIds) {
        this.timeoffService.cancelTimeOffRequest(rId).subscribe({
          next: () => {
            canceledCount++;
            if (canceledCount === reqIds.length && !hasError) {
              this.isCancelling = false;
              this.toastService.showSuccess('Time-off request cancelled successfully.');
              this.closeDetailsModal();
              this.loadRequests();
              this.loadBalances();
            }
          },
          error: (err) => {
            console.error('Error cancelling request', err);
            this.isCancelling = false;
            if (!hasError) {
              hasError = true;
              this.toastService.showError(err?.error?.detail || 'Failed to cancel time-off request.');
            }
          }
        });
      }
    }
  }

  downloadAttachment(fileName: string): void {
    this.toastService.showInfo(`Downloading attachment: ${fileName}`);
  }
}
