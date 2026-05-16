import { Component, EventEmitter, Input, OnDestroy, OnInit, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { finalize } from 'rxjs/operators';
import { Subscription } from 'rxjs';

import { EmployeeService } from '../../../../../../core/services/employee.service';
import { EmployeeCredentials } from '../../../../../../core/models/employee.model';

@Component({
  selector: 'app-employee-credential-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './employee-credential-modal.html',
  styleUrls: ['./employee-credential-modal.css']
})
export class EmployeeCredentialModalComponent implements OnInit, OnDestroy {
  @Input() employeeId!: string;
  @Output() closed = new EventEmitter<void>();

  credentials: EmployeeCredentials | null = null;
  isLoading = true;
  errorMessage = '';

  private subscription?: Subscription;

  constructor(
    private employeeService: EmployeeService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const employeeId = String(this.employeeId ?? '').trim();
    if (!employeeId) {
      this.isLoading = false;
      this.errorMessage = 'Employee ID is missing.';
      return;
    }
    if (!/^\d+$/.test(employeeId)) {
      this.isLoading = false;
      this.errorMessage = 'Invalid employee ID.';
      return;
    }

    console.log('EmployeeCredentialModal: Fetching credentials for ID:', employeeId);
    this.isLoading = true;
    this.errorMessage = '';
    this.credentials = null;

    this.subscription = this.employeeService.getEmployeeCredentials(employeeId)
      .pipe(
        finalize(() => {
          console.log('EmployeeCredentialModal: Load finished for ID:', employeeId);
          this.isLoading = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (credentials) => {
          console.log('EmployeeCredentialModal: Credentials received:', credentials);
          if (credentials) {
            this.credentials = credentials;
          } else {
            this.errorMessage = 'No account credentials found for this employee.';
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('EmployeeCredentialModal: Credential load error:', err);
          this.errorMessage = err?.error?.detail || err?.message || 'Failed to load credentials. Please try again.';
          this.credentials = null;
          this.cdr.markForCheck();
        }
      });
  }

  ngOnDestroy(): void {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  copy(text: string): void {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard');
  }

  close(): void {
    this.closed.emit();
  }
}
