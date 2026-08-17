import { Component, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Observable, BehaviorSubject, combineLatest } from 'rxjs';
import { switchMap, tap, map, shareReplay } from 'rxjs/operators';
import { Employee, PaginatedResult } from '../../../../core/models/employee.model';
import { EmployeeService } from '../../../../core/services/employee.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { AuthService } from '../../../../core/services/auth.service';

import { EmployeeViewModalComponent } from './modals/employee-view-modal/employee-view-modal';
import { EmployeeEditModalComponent } from './modals/employee-edit-modal/employee-edit-modal';
import { EmployeeCredentialModalComponent } from './modals/employee-credential-modal/employee-credential-modal';
import { EmployeeAddModalComponent } from './modals/employee-add-modal/employee-add-modal';

import { MasterDataService } from '../../../../core/services/master-data.service';

@Component({
  selector: 'app-employees',
  standalone: true,
  imports: [
    CommonModule, 
    ReactiveFormsModule, 
    CustomSelectComponent, 
    RouterModule,
    EmployeeViewModalComponent,
    EmployeeEditModalComponent,
    EmployeeCredentialModalComponent,
    EmployeeAddModalComponent
  ],
  templateUrl: './employees.html',
  styleUrl: './employees.css'
})
export class Employees implements OnInit {
  currentUser: any = null;
  deleteModalOpen = false;
  employeeToDelete: Employee | null = null;
  searchControl = new FormControl('');
  departmentControl = new FormControl('');
  typeControl = new FormControl('');
  statusControl = new FormControl('');

  departments = ['Engineering', 'Human Resources', 'Finance', 'Marketing', 'Sales', 'Support'];
  employeeTypes = ['Full-Time', 'Part-Time', 'Contract', 'Intern'];
  statuses = ['Active', 'Inactive'];

  get departmentsOptions() { return [{label: 'All Departments', value: ''}, ...this.departments.map(d => ({label: d, value: d}))]; }
  get typesOptions() { return [{label: 'All Types', value: ''}, ...this.employeeTypes.map(t => ({label: t, value: t}))]; }
  get statusOptions() { return [{label: 'All Statuses', value: ''}, ...this.statuses.map(s => ({label: s, value: s}))]; }

  pageSubject = new BehaviorSubject<number>(1);
  pageSize = 10;
  
  isLoading$ = new BehaviorSubject<boolean>(true);
  employeesData$!: Observable<PaginatedResult<Employee>>;
  paginationArray$!: Observable<number[]>;

  searchTrigger$ = new BehaviorSubject<boolean>(true);
  userRoleLabel = 'Admin';

  // Stats for the top overview cards
  stats = {
    total: 128,
    active: 112,
    onLeave: 10,
    inactive: 6,
    docCompletePct: 62,
    docCompleteCount: 79,
    docPartialPct: 28,
    docPartialCount: 36,
    docIncompletePct: 10,
    docIncompleteCount: 13
  };

  // Modal State
  activeModal: 'add' | 'view' | 'edit' | 'credential' | null = null;
  selectedEmployee: Employee | null = null;

  sortColumn: string = '';
  sortAscending: boolean = true;

  constructor(
    private readonly employeeService: EmployeeService, 
    private readonly masterDataService: MasterDataService,
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.userRoleLabel = this.currentUser?.role === 'admin' ? 'Admin' : 'HR';

    this.masterDataService.getDepartments().subscribe({
      next: (depts) => {
        if (depts && depts.length > 0) {
          this.departments = depts.map(d => d.name);
        }
      },
      error: (err) => console.warn('Failed to load departments for employee filter:', err)
    });

    this.employeesData$ = combineLatest([
      this.searchTrigger$,
      this.pageSubject.asObservable()
    ]).pipe(
      tap(() => this.isLoading$.next(true)),
      switchMap(([_, page]) => {
        const excludeHr = this.router.url.includes('/hr-dashboard');
        return this.employeeService.getEmployees(
             page, 
             this.pageSize, 
             this.searchControl.value || '', 
             this.departmentControl.value || '', 
             this.typeControl.value || '', 
             this.statusControl.value || '',
             excludeHr
        );
      }),
      tap((result) => {
        this.isLoading$.next(false);
        this.updateStats(result.total);
      }),
      shareReplay(1)
    );

    this.paginationArray$ = this.employeesData$.pipe(
      map(res => {
        const totalPages = Math.ceil(res.total / this.pageSize);
        return Array.from({length: totalPages}, (_, i) => i + 1);
      })
    );
  }

  updateStats(total: number) {
    if (total <= 0) {
      this.stats.total = 0;
      this.stats.active = 0;
      this.stats.onLeave = 0;
      this.stats.inactive = 0;
      this.stats.docCompleteCount = 0;
      this.stats.docPartialCount = 0;
      this.stats.docIncompleteCount = 0;
      return;
    }

    this.stats.total = total;
    this.stats.active = Math.max(1, Math.round(total * 0.875));
    this.stats.onLeave = Math.max(0, Math.round(total * 0.08));
    this.stats.inactive = Math.max(0, total - this.stats.active - this.stats.onLeave);

    this.stats.docCompleteCount = Math.round(total * 0.62);
    this.stats.docPartialCount = Math.round(total * 0.28);
    this.stats.docIncompleteCount = Math.max(0, total - this.stats.docCompleteCount - this.stats.docPartialCount);
  }

  setPage(page: number) {
    this.pageSubject.next(page);
  }

  onPageSizeChange(event: any) {
    const size = parseInt(event.target.value, 10);
    if (!isNaN(size) && size > 0) {
      this.pageSize = size;
      this.setPage(1);
    }
  }

  onSearch() {
    this.pageSubject.next(1);
    this.searchTrigger$.next(true);
  }

  onReset() {
    this.searchControl.setValue('');
    this.departmentControl.setValue('');
    this.typeControl.setValue('');
    this.statusControl.setValue('');
    this.onSearch();
  }

  sort(column: string) {
    if (this.sortColumn === column) {
      this.sortAscending = !this.sortAscending;
    } else {
      this.sortColumn = column;
      this.sortAscending = true;
    }
  }

  trackById(index: number, employee: Employee): string {
    return employee.id;
  }

  getInitials(name: string): string {
    if (!name) return 'EM';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  getAvatarColor(name: string): { bg: string, text: string } {
    const colors = [
      { bg: '#DBEAFE', text: '#2563EB' }, // blue
      { bg: '#DCFCE7', text: '#15803D' }, // green
      { bg: '#FEF3C7', text: '#D97706' }, // amber
      { bg: '#F3E8FF', text: '#9333EA' }, // purple
      { bg: '#FEE2E2', text: '#DC2626' }, // red
      { bg: '#E0F2FE', text: '#0284C7' }, // cyan
      { bg: '#CCFBF1', text: '#0D9488' }, // teal
      { bg: '#FCE7F3', text: '#DB2777' }  // pink
    ];
    if (!name) return colors[0];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
  }

  getDocCompletion(emp: Employee): { count: number, total: number, label: string, color: string } {
    const seed = (emp.id || emp.employeeCode || emp.name || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const mod = seed % 3;
    if (mod === 0) {
      return { count: 8, total: 8, label: 'Complete', color: '#10B981' };
    } else if (mod === 1) {
      const count = 5 + (seed % 3); // 5 or 6 or 7
      return { count, total: 8, label: 'Partial', color: '#F59E0B' };
    } else {
      const count = 1 + (seed % 2); // 1 or 2
      return { count, total: 8, label: 'Incomplete', color: '#EF4444' };
    }
  }

  getDocCountBadge(emp: Employee): { hasImg: boolean, extra: number } {
    const seed = (emp.id || emp.employeeCode || emp.name || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const extra = (seed % 4); // 0, 1, 2, or 3
    return { hasImg: (seed % 2 === 0), extra };
  }

  getVisiblePages(pages: number[], current: number): number[] {
    const total = pages.length;
    if (total <= 7) return pages;

    if (current <= 3) {
      return [1, 2, 3, 4, -1, total];
    } else if (current >= total - 2) {
      return [1, -1, total - 3, total - 2, total - 1, total];
    } else {
      return [1, -1, current - 1, current, current + 1, -1, total];
    }
  }

  openViewModal(employee: Employee): void {
    this.selectedEmployee = employee;
    this.activeModal = 'view';
  }

  openEditModal(employee: Employee): void {
    this.selectedEmployee = employee;
    this.activeModal = 'edit';
  }

  openCredentialModal(employee: Employee): void {
    this.selectedEmployee = employee;
    this.activeModal = 'credential';
  }

  openAddModal(): void {
    this.activeModal = 'add';
  }

  onModalClose(refresh: boolean = false): void {
    this.activeModal = null;
    this.selectedEmployee = null;
    if (refresh) {
      this.onSearch();
    }
  }

  confirmDelete(employee: Employee): void {
    this.employeeToDelete = employee;
    this.deleteModalOpen = true;
  }

  closeDeleteModal(): void {
    this.deleteModalOpen = false;
    this.employeeToDelete = null;
  }

  executeDelete(): void {
    if (!this.employeeToDelete) return;
    const employee = this.employeeToDelete;
    this.closeDeleteModal();
    this.isLoading$.next(true);
    this.employeeService.deleteEmployee(employee.id).subscribe({
      next: () => {
        this.onSearch();
      },
      error: (err) => {
        this.isLoading$.next(false);
        console.error('Failed to delete employee:', err);
        alert(err?.error?.detail || 'An error occurred while deleting the employee.');
      }
    });
  }
}
