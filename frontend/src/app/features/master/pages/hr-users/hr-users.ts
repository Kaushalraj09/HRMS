import { ChangeDetectionStrategy, Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { BehaviorSubject, Observable, combineLatest } from 'rxjs';
import { map, shareReplay, switchMap, tap } from 'rxjs/operators';
import { RouterModule } from '@angular/router';

import { PaginatedResult } from '../../../../core/models/employee.model';
import { HrUser } from '../../../../core/models/hr.model';
import { HrService } from '../../../../core/services/hr.service';
import { AuthService } from '../../../../core/services/auth.service';
import { EmployeeService } from '../../../../core/services/employee.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { HrAddModalComponent } from './modals/hr-add-modal/hr-add-modal';

@Component({
  selector: 'app-hr-users',
  standalone: true,
  imports: [
    CommonModule, 
    ReactiveFormsModule, 
    RouterModule, 
    CustomSelectComponent,
    HrAddModalComponent
  ],
  templateUrl: './hr-users.html',
  styleUrl: './hr-users.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HrUsersComponent implements OnInit, OnDestroy {
  currentUser: any = null;
  deleteModalOpen = false;
  hrToDelete: HrUser | null = null;
  activeModal: 'add' | null = null;
  searchControl = new FormControl('');
  statusControl = new FormControl('');

  pageSubject = new BehaviorSubject<number>(1);
  pageSize = 8;
  reloadSubject = new BehaviorSubject<boolean>(true);
  isLoading$ = new BehaviorSubject<boolean>(true);

  hrData$!: Observable<PaginatedResult<HrUser>>;
  pages$!: Observable<number[]>;

  statusOptions = [
    { label: 'Active (Default)', value: '' },
    { label: 'All Statuses', value: 'all' },
    { label: 'Inactive', value: 'Inactive' }
  ];

  toastMessage: string | null = null;
  toastSubMessage: string = '';
  isErrorToast: boolean = false;
  private toastTimeout: any = null;

  constructor(
    private readonly hrService: HrService,
    private readonly authService: AuthService,
    private readonly employeeService: EmployeeService,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.hrData$ = combineLatest([this.reloadSubject, this.pageSubject]).pipe(
      tap(() => this.isLoading$.next(true)),
      switchMap(([_, page]: [boolean, number]) =>
        this.hrService.getHrUsers(page, this.pageSize, this.searchControl.value || '', this.statusControl.value || '')
      ),
      tap(() => this.isLoading$.next(false)),
      shareReplay(1)
    );

    this.pages$ = this.hrData$.pipe(
      map((result: PaginatedResult<HrUser>) => Array.from({ length: Math.max(1, Math.ceil(result.total / this.pageSize)) }, (_: unknown, index: number) => index + 1))
    );
  }

  ngOnDestroy(): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
    }
  }

  showToast(message: string, isError: boolean = false, subMessage: string = ''): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
    }
    this.toastMessage = message;
    this.isErrorToast = isError;
    this.toastSubMessage = subMessage;
    this.cdr.markForCheck();
    this.cdr.detectChanges();
    this.toastTimeout = setTimeout(() => {
      this.toastMessage = null;
      this.toastSubMessage = '';
      this.cdr.markForCheck();
      this.cdr.detectChanges();
    }, 2800);
  }

  closeToast(): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
    }
    this.toastMessage = null;
    this.toastSubMessage = '';
    this.cdr.markForCheck();
    this.cdr.detectChanges();
  }

  onSearch(): void {
    this.pageSubject.next(1);
    this.reloadSubject.next(true);
  }

  onReset(): void {
    this.searchControl.setValue('');
    this.statusControl.setValue('');
    this.onSearch();
  }

  setPage(page: number): void {
    this.pageSubject.next(page);
  }

  trackById(_: number, hr: HrUser): string {
    return hr.id;
  }

  openAddModal(): void {
    this.activeModal = 'add';
  }

  onModalClose(refresh: boolean = false): void {
    this.activeModal = null;
    if (refresh) {
      this.onSearch();
      this.showToast('HR User Created Successfully!', false, 'Credentials setup email has been dispatched to their inbox.');
    }
    this.cdr.markForCheck();
  }

  confirmDelete(hr: HrUser): void {
    this.hrToDelete = hr;
    this.deleteModalOpen = true;
    this.cdr.markForCheck();
  }

  closeDeleteModal(): void {
    this.deleteModalOpen = false;
    this.hrToDelete = null;
    this.cdr.markForCheck();
  }

  executeDelete(): void {
    if (!this.hrToDelete) return;
    const hr = this.hrToDelete;
    this.closeDeleteModal();
    this.isLoading$.next(true);
    this.employeeService.deleteEmployee(hr.id).subscribe({
      next: () => {
        this.showToast('HR User Deleted Successfully', false, `${hr.fullName} has been removed from active HR directories.`);
        this.onSearch();
      },
      error: (err: any) => {
        this.isLoading$.next(false);
        console.error('Failed to delete HR user:', err);
        this.showToast('Failed to Delete HR User', true, err?.error?.detail || 'An error occurred while deleting.');
        this.cdr.markForCheck();
      }
    });
  }
}

