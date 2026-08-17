import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportService } from '../../../../core/services/report.service';
import { AttendanceSummaryRow, LateArrivalRow, MissingPunchRow, LeaveUsageRow } from '../../../../core/models/report.model';

import { MasterDataService } from '../../../../core/services/master-data.service';

@Component({
  selector: 'app-hr-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reports.html',
  styleUrls: ['./reports.css']
})
export class HRReportsComponent implements OnInit {
  activeTab: 'summary' | 'late' | 'missing' | 'leave' = 'summary';

  // Filters
  startDate: string = '';
  endDate: string = '';
  department: string = '';
  search: string = '';

  // Pagination
  page: number = 1;
  pageSize: number = 10;
  totalItems: number = 0;
  totalPages: number = 1;

  // Data lists
  summaryData: AttendanceSummaryRow[] = [];
  lateData: LateArrivalRow[] = [];
  missingData: MissingPunchRow[] = [];
  leaveData: LeaveUsageRow[] = [];

  isLoading: boolean = false;

  departments: string[] = ['Engineering', 'Sales', 'Marketing', 'Human Resources', 'Finance', 'Operations'];

  constructor(
    private readonly reportService: ReportService,
    private readonly masterDataService: MasterDataService,
    private readonly cdr: ChangeDetectorRef
  ) {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    this.endDate = this.formatDate(today);
    this.startDate = this.formatDate(thirtyDaysAgo);
  }

  ngOnInit(): void {
    this.masterDataService.getDepartments().subscribe({
      next: (depts) => {
        if (depts && depts.length > 0) {
          this.departments = depts.map(d => d.name);
          this.cdr.markForCheck();
        }
      },
      error: (err) => console.warn('Failed to load departments for HR report filter:', err)
    });
    this.loadReport();
  }

  private formatDate(d: Date): string {
    const month = '' + (d.getMonth() + 1);
    const day = '' + d.getDate();
    const year = d.getFullYear();
    return [year, month.padStart(2, '0'), day.padStart(2, '0')].join('-');
  }

  switchTab(tab: 'summary' | 'late' | 'missing' | 'leave'): void {
    this.activeTab = tab;
    this.page = 1;
    this.loadReport();
  }

  loadReport(): void {
    this.isLoading = true;
    switch (this.activeTab) {
      case 'summary':
        this.reportService.getAttendanceSummary(this.startDate, this.endDate, this.department, this.search, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.summaryData = res.data;
              this.totalItems = res.total;
              this.totalPages = res.pages;
              this.updatePageNumbers();
              this.isLoading = false;
              this.cdr.detectChanges();
            },
            error: () => {
              this.isLoading = false;
              this.cdr.detectChanges();
            }
          });
        break;
      case 'late':
        this.reportService.getLateArrivals(this.startDate, this.endDate, this.department, this.search, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.lateData = res.data;
              this.totalItems = res.total;
              this.totalPages = res.pages;
              this.updatePageNumbers();
              this.isLoading = false;
              this.cdr.detectChanges();
            },
            error: () => {
              this.isLoading = false;
              this.cdr.detectChanges();
            }
          });
        break;
      case 'missing':
        this.reportService.getMissingPunches(this.startDate, this.endDate, this.department, this.search, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.missingData = res.data;
              this.totalItems = res.total;
              this.totalPages = res.pages;
              this.updatePageNumbers();
              this.isLoading = false;
              this.cdr.detectChanges();
            },
            error: () => {
              this.isLoading = false;
              this.cdr.detectChanges();
            }
          });
        break;
      case 'leave':
        this.reportService.getLeaveUsage(this.startDate, this.endDate, this.department, this.search, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.leaveData = res.data;
              this.totalItems = res.total;
              this.totalPages = res.pages;
              this.updatePageNumbers();
              this.isLoading = false;
              this.cdr.detectChanges();
            },
            error: () => {
              this.isLoading = false;
              this.cdr.detectChanges();
            }
          });
        break;
    }
  }

  applyFilters(): void {
    this.page = 1;
    this.loadReport();
  }

  clearFilters(): void {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    this.endDate = this.formatDate(today);
    this.startDate = this.formatDate(thirtyDaysAgo);
    this.department = '';
    this.search = '';
    this.page = 1;
    this.loadReport();
  }

  exportCsv(): void {
    let endpoint = '';
    const filters: any = {
      startDate: this.startDate,
      endDate: this.endDate,
      department: this.department,
      search: this.search
    };

    switch (this.activeTab) {
      case 'summary':
        endpoint = 'hr/attendance-summary';
        break;
      case 'late':
        endpoint = 'hr/late-arrivals';
        break;
      case 'missing':
        endpoint = 'hr/missing-punches';
        break;
      case 'leave':
        endpoint = 'hr/leave-usage';
        break;
    }

    this.reportService.exportReportCsv(endpoint, filters).subscribe({
      next: (blob) => {
        const filename = `${this.activeTab}_report_${new Date().toISOString().split('T')[0]}.pdf`;
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: (err) => console.error('Export failed', err)
    });
  }

  pageNumbers: number[] = [1];

  private updatePageNumbers(): void {
    this.pageNumbers = Array.from({ length: this.totalPages }, (_, i) => i + 1);
  }

  onPageChange(p: number): void {
    if (p >= 1 && p <= this.totalPages) {
      this.page = p;
      this.loadReport();
    }
  }

  formatWorkingHours(minutes: number): string {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hrs}h ${mins}m`;
  }

  formatStatusText(status: string): string {
    if (!status) return '';
    return status.replace(/_/g, ' ')
                 .toLowerCase()
                 .split(' ')
                 .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                 .join(' ');
  }
}
