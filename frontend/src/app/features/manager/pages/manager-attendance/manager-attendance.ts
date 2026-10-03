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

  activePreset: string = 'all';

  constructor(
    private readonly managerService: ManagerService,
    private readonly toastService: ToastService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.setQuickPreset('all');
  }

  private formatDateStr(d: Date): string {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  setQuickPreset(preset: string): void {
    this.activePreset = preset;
    const now = new Date();
    if (preset === 'today') {
      const todayStr = this.formatDateStr(now);
      this.fromDate = todayStr;
      this.toDate = todayStr;
    } else if (preset === 'yesterday') {
      const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      const yStr = this.formatDateStr(yesterday);
      this.fromDate = yStr;
      this.toDate = yStr;
    } else if (preset === 'week') {
      const pastWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      this.fromDate = this.formatDateStr(pastWeek);
      this.toDate = this.formatDateStr(now);
    } else if (preset === 'month') {
      const past30 = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      this.fromDate = this.formatDateStr(past30);
      this.toDate = this.formatDateStr(now);
    } else if (preset === 'all') {
      this.fromDate = '';
      this.toDate = '';
    }
    this.currentPage = 1;
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
    this.activePreset = 'custom';
    this.currentPage = 1;
    this.loadAttendance();
  }

  resetFilters(): void {
    this.statusFilter = '';
    this.searchQuery = '';
    this.setQuickPreset('all');
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
