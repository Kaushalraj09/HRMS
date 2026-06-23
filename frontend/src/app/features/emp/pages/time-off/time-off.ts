import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TimeOffModalComponent } from '../emp-dashboard/modals/time-off-modal/time-off-modal';

@Component({
  selector: 'app-emp-time-off',
  standalone: true,
  imports: [CommonModule, FormsModule, TimeOffModalComponent],
  templateUrl: './time-off.html',
  styleUrls: ['./time-off.css']
})
export class EmpTimeOffComponent implements OnInit, OnDestroy {
  requests: any[] = [];
  
  // Balance metrics
  approvedHours = 0;
  remainingHours = 9.0;
  requestedHours = 0;

  // Pagination state
  page = 1;
  pageSize = 10;
  totalItems = 0;

  showTimeOffModal = false;

  private readonly subscriptions = new Subscription();

  constructor(
    private readonly attendanceService: AttendanceService,
    private readonly authService: AuthService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadRequests();
    this.loadBalances();

    // WebSocket updates
    this.subscriptions.add(
      this.attendanceService.timeoffUpdate$.subscribe(() => {
        this.loadRequests();
        this.loadBalances();
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadRequests(): void {
    this.attendanceService.getMyTimeOffRequests(this.page, this.pageSize).subscribe({
      next: (res) => {
        this.requests = res.items;
        this.totalItems = res.totalItems;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading time off requests', err);
      }
    });
  }

  loadBalances(): void {
    this.attendanceService.getTodayAttendanceState().subscribe({
      next: (state) => {
        this.approvedHours = (state.approvedSeconds || 0) / 3600;
        this.remainingHours = (state.remainingSeconds || 0) / 3600;
        this.cdr.detectChanges();
      }
    });

    this.attendanceService.getMyTimeOffRequests(1, 1000).subscribe({
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

  selectedRequest: any = null;

  viewRequestDetails(req: any): void {
    this.selectedRequest = req;
  }

  closeDetailsModal(): void {
    this.selectedRequest = null;
  }

  downloadAttachment(fileName: string): void {
    alert(`Downloading attachment: ${fileName}`);
  }
}
