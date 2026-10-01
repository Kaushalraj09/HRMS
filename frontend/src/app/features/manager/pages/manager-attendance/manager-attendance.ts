import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ManagerService } from '../../../../core/services/manager.service';
import { ToastService } from '../../../../core/services/toast.service';
import { CustomDatepickerComponent } from '../../../../shared/components/custom-datepicker/custom-datepicker';
import { CustomSelectComponent, SelectOption } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-manager-attendance',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomDatepickerComponent, CustomSelectComponent],
  templateUrl: './manager-attendance.html',
  styleUrls: ['./manager-attendance.css']
})
export class ManagerAttendanceComponent implements OnInit {
  attendanceRecords: any[] = [];
  isLoading = true;

  // Filters
  searchQuery = '';
  statusFilter = '';
  fromDate = '';
  toDate = '';

  statusOptions: SelectOption[] = [
    { label: 'All Statuses', value: '' },
    { label: 'Present', value: 'Present' },
    { label: 'Absent', value: 'Absent' },
    { label: 'On Leave', value: 'On Leave' },
    { label: 'Late', value: 'Late' },
    { label: 'Half Day', value: 'Half Day' }
  ];

  // Pagination
  currentPage = 1;
  pageSize = 10;
  totalRecords = 0;
  totalPages = 1;

  constructor(
    private readonly managerService: ManagerService,
    private readonly toastService: ToastService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Default to current date
    const today = new Date().toISOString().split('T')[0];
    this.fromDate = today;
    this.toDate = today;
    this.loadAttendance();
  }

  loadAttendance(): void {
    this.isLoading = true;
    this.managerService
      .getTeamAttendance({
        page: this.currentPage,
        limit: this.pageSize,
        fromDate: this.fromDate || undefined,
        toDate: this.toDate || undefined,
        status: this.statusFilter || undefined,
        search: this.searchQuery || undefined
      })
      .subscribe({
        next: res => {
          this.attendanceRecords = res.items || [];
          this.totalRecords = res.total;
          this.totalPages = res.totalPages || Math.ceil(this.totalRecords / this.pageSize) || 1;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: err => {
          this.isLoading = false;
          this.toastService.showError(err?.error?.detail || 'Failed to load team attendance');
          this.cdr.markForCheck();
        }
      });
  }

  applyFilters(): void {
    this.currentPage = 1;
    this.loadAttendance();
  }

  resetFilters(): void {
    const today = new Date().toISOString().split('T')[0];
    this.fromDate = today;
    this.toDate = today;
    this.statusFilter = '';
    this.searchQuery = '';
    this.currentPage = 1;
    this.loadAttendance();
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadAttendance();
    }
  }

  formatTime(timeStr?: string): string {
    if (!timeStr) return '—';
    // If it's already HH:MM or HH:MM:SS or formatted
    return timeStr.slice(0, 5);
  }
}
