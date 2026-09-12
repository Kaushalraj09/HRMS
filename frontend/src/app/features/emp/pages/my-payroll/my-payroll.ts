import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { PayrollService } from '../../../../core/services/payroll.service';
import { ToastService } from '../../../../core/services/toast.service';
import {
  EmployeeSalaryAssignment,
  Payslip
} from '../../../../core/models/payroll.model';

@Component({
  selector: 'app-my-payroll',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './my-payroll.html',
  styleUrls: ['./my-payroll.css']
})
export class MyPayrollComponent implements OnInit, OnDestroy {
  activeTab: 'breakdown' | 'payslips' | 'history' = 'breakdown';
  isLoading = false;
  private subs: Subscription = new Subscription();

  // Salary Breakdown
  salaryAssignment: EmployeeSalaryAssignment | null = null;
  earningsComponents: any[] = [];
  deductionsComponents: any[] = [];
  employerContributions: any[] = [];

  // Payslips
  payslips: Payslip[] = [];
  payslipsTotal = 0;
  isDownloadingPdf = false;

  // History
  salaryHistory: EmployeeSalaryAssignment[] = [];

  constructor(
    private payrollService: PayrollService,
    private toast: ToastService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadMySalary();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  switchTab(tab: 'breakdown' | 'payslips' | 'history'): void {
    this.activeTab = tab;
    if (tab === 'breakdown') {
      this.loadMySalary();
    } else if (tab === 'payslips') {
      this.loadMyPayslips();
    } else if (tab === 'history') {
      this.loadMySalaryHistory();
    }
  }

  loadMySalary(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getMySalary().subscribe({
        next: (salary) => {
          this.salaryAssignment = salary;
          this.earningsComponents = salary.breakdown?.earnings || (salary.components || []).filter(c => c.component_type === 'EARNING');
          this.deductionsComponents = salary.breakdown?.deductions || (salary.components || []).filter(c => c.component_type === 'DEDUCTION');
          this.employerContributions = salary.breakdown?.employer_contributions || (salary.components || []).filter(c => c.component_type === 'STATUTORY_EMPLOYER');
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          if (err.status !== 404) {
            this.toast.showError(err?.error?.detail || 'Failed to load salary structure', 'Error');
          }
        }
      })
    );
  }

  loadMyPayslips(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getMyPayslips(0, 50).subscribe({
        next: (res) => {
          this.payslips = res.items;
          this.payslipsTotal = res.total;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load payslips', 'Error');
        }
      })
    );
  }

  loadMySalaryHistory(): void {
    this.isLoading = true;
    this.subs.add(
      this.payrollService.getMySalaryHistory().subscribe({
        next: (history) => {
          this.salaryHistory = history;
          this.isLoading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.isLoading = false;
          this.toast.showError(err?.error?.detail || 'Failed to load salary history', 'Error');
        }
      })
    );
  }

  downloadPayslipPdf(payslip: Payslip): void {
    this.isDownloadingPdf = true;
    this.payrollService.downloadPayslipPdf(payslip.id).subscribe({
      next: (blob) => {
        this.isDownloadingPdf = false;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Payslip_${payslip.payslip_number || payslip.id}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toast.showSuccess('Payslip PDF downloaded successfully', 'Downloaded');
      },
      error: () => {
        this.isDownloadingPdf = false;
        this.toast.showError('Could not download payslip PDF', 'Error');
      }
    });
  }

  formatCurrency(val: number | null | undefined): string {
    if (val === null || val === undefined || isNaN(val)) return '₹0.00';
    return '₹' + Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
}
