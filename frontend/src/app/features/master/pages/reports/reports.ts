import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportService } from '../../../../core/services/report.service';
import { HrWorkloadRow, EmployeeStatusRow, LoginActivitySummaryRow } from '../../../../core/models/report.model';

@Component({
  selector: 'app-admin-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reports.html',
  styleUrls: ['./reports.css']
})
export class AdminReportsComponent implements OnInit {
  activeTab: 'workload' | 'status' | 'login' = 'workload';

  // Filters
  startDate: string = '';
  endDate: string = '';
  department: string = '';
  search: string = '';
  statusFilter: string = '';

  // Pagination
  page: number = 1;
  pageSize: number = 10;
  totalItems: number = 0;
  totalPages: number = 1;

  // Data lists
  workloadData: HrWorkloadRow[] = [];
  statusData: EmployeeStatusRow[] = [];
  loginData: LoginActivitySummaryRow[] = [];

  isLoading: boolean = false;

  departments: string[] = ['Engineering', 'Sales', 'Marketing', 'Human Resources', 'Finance', 'Operations'];
  statuses: string[] = ['Active', 'Inactive'];

  constructor(
    private readonly reportService: ReportService,
    private readonly cdr: ChangeDetectorRef
  ) {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    this.endDate = this.formatDate(today);
    this.startDate = this.formatDate(thirtyDaysAgo);
  }

  ngOnInit(): void {
    this.loadReport();
  }

  private formatDate(d: Date): string {
    const month = '' + (d.getMonth() + 1);
    const day = '' + d.getDate();
    const year = d.getFullYear();
    return [year, month.padStart(2, '0'), day.padStart(2, '0')].join('-');
  }

  switchTab(tab: 'workload' | 'status' | 'login'): void {
    this.activeTab = tab;
    this.page = 1;
    this.loadReport();
  }

  loadReport(): void {
    this.isLoading = true;
    switch (this.activeTab) {
      case 'workload':
        this.reportService.getHrWorkload(this.startDate, this.endDate, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.workloadData = res.data;
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
      case 'status':
        this.reportService.getEmployeeStatus(this.department, this.search, this.statusFilter, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.statusData = res.data;
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
      case 'login':
        this.reportService.getLoginActivitySummary(this.startDate, this.endDate, this.page, this.pageSize)
          .subscribe({
            next: (res) => {
              this.loginData = res.data;
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
    this.statusFilter = '';
    this.page = 1;
    this.loadReport();
  }

  exportCsv(): void {
    let endpoint = '';
    let filters: any = {};

    switch (this.activeTab) {
      case 'workload':
        endpoint = 'admin/hr-workload';
        filters = { startDate: this.startDate, endDate: this.endDate };
        break;
      case 'status':
        endpoint = 'admin/employee-status';
        filters = { department: this.department, search: this.search, status: this.statusFilter };
        break;
      case 'login':
        endpoint = 'admin/login-activity';
        filters = { startDate: this.startDate, endDate: this.endDate };
        break;
    }

    this.reportService.exportReportCsv(endpoint, filters).subscribe({
      next: (blob) => {
        const filename = `admin_${this.activeTab}_report_${new Date().toISOString().split('T')[0]}.csv`;
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
}
