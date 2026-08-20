import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Observable, BehaviorSubject, combineLatest, of, forkJoin } from 'rxjs';
import { switchMap, tap, map, shareReplay, catchError } from 'rxjs/operators';
import { Employee, PaginatedResult } from '../../../../core/models/employee.model';
import { EmployeeService } from '../../../../core/services/employee.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { AuthService } from '../../../../core/services/auth.service';

import { EmployeeViewModalComponent } from './modals/employee-view-modal/employee-view-modal';
import { EmployeeEditModalComponent } from './modals/employee-edit-modal/employee-edit-modal';
import { EmployeeCredentialModalComponent } from './modals/employee-credential-modal/employee-credential-modal';
import { EmployeeAddModalComponent } from './modals/employee-add-modal/employee-add-modal';

import { MasterDataService } from '../../../../core/services/master-data.service';
import { DocumentService } from '../../../../core/services/document.service';
import { EmployeeDocumentsPageResponse, EmployeeDocumentItem } from '../../../../core/models/document.model';

export interface EmployeeDocFileIcon {
  type: 'pdf' | 'word' | 'excel' | 'image' | 'other';
  title: string;
  iconClass: string;
}

export interface EmployeeDocSummaryInfo {
  uploadedCount: number;
  verifiedCount: number;
  totalRequired: number;
  completionPct: number;
  label: string;
  color: string;
  fileIcons: EmployeeDocFileIcon[];
  extraCount: number;
}

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

  departments: string[] = ['Engineering', 'Human Resources', 'Finance', 'Marketing', 'Sales', 'Support'];
  types: string[] = ['Full Time', 'Part Time', 'Contract'];
  statuses: string[] = ['Active', 'Inactive', 'On Leave'];

  get departmentsOptions() { return [{label: 'All Departments', value: ''}, ...this.departments.map(d => ({label: d, value: d}))]; }
  get typesOptions() { return [{label: 'All Types', value: ''}, ...this.types.map(t => ({label: t, value: t}))]; }
  get statusOptions() { return [{label: 'All Statuses', value: ''}, ...this.statuses.map(s => ({label: s, value: s}))]; }

  // Pagination & Loading State
  pageSubject = new BehaviorSubject<number>(1);
  pageSize = 10;
  totalRecords = 0;
  isLoading$ = new BehaviorSubject<boolean>(true);
  employeesData$!: Observable<{ data: Employee[], total: number }>;
  paginationArray$!: Observable<number[]>;
  searchTrigger$ = new BehaviorSubject<boolean>(true);
  userRoleLabel = 'Admin';

  // Stats for the top overview cards
  stats = {
    total: 0,
    active: 0,
    onLeave: 0,
    inactive: 0,
    docCompletePct: 0,
    docCompleteCount: 0,
    docPartialPct: 0,
    docPartialCount: 0,
    docIncompletePct: 0,
    docIncompleteCount: 0
  };

  // Modal State
  activeModal: 'add' | 'view' | 'edit' | 'credential' | null = null;
  selectedEmployee: Employee | null = null;
  viewModalTab: 'details' | 'documents' = 'details';

  sortColumn: string = '';
  sortAscending: boolean = true;
  docCompletionMap: Record<string, { count: number, total: number, label: string, color: string }> = {};
  docDataMap: Record<string, EmployeeDocSummaryInfo> = {};

  constructor(
    private readonly employeeService: EmployeeService, 
    private readonly masterDataService: MasterDataService,
    private readonly documentService: DocumentService,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.userRoleLabel = this.currentUser?.role === 'admin' ? 'Admin' : 'HR';

    this.masterDataService.getDepartments().subscribe({
      next: (depts) => {
        if (depts && depts.length > 0) {
          this.departments = depts.map(d => d.name);
          this.cdr.detectChanges();
        }
      },
      error: (err) => console.warn('Failed to load departments for employee filter:', err)
    });

    this.loadHrDocKpis();

    this.employeesData$ = combineLatest([
      this.searchTrigger$,
      this.pageSubject.asObservable()
    ]).pipe(
      tap(() => {
        this.isLoading$.next(true);
        this.cdr.detectChanges();
      }),
      switchMap(() => {
        return this.employeeService.getEmployees(
             this.pageSubject.value, 
             this.pageSize, 
             this.searchControl.value || '', 
             this.departmentControl.value || '', 
             this.typeControl.value || '', 
             this.statusControl.value || '',
             false
        );
      }),
      tap((result) => {
        this.isLoading$.next(false);
        this.updateStats(result.total);
        if (result.data) {
          this.loadDocumentCompletions(result.data);
        }
        this.cdr.detectChanges();
      }),
      catchError((err) => {
        this.isLoading$.next(false);
        console.error('Failed to load employees:', err);
        this.cdr.detectChanges();
        return of({ data: [], total: 0 });
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
      this.cdr.detectChanges();
      return;
    }

    this.stats.total = total;
    this.stats.active = Math.max(1, Math.round(total * 0.875));
    this.stats.onLeave = Math.max(0, Math.round(total * 0.08));
    this.stats.inactive = Math.max(0, total - this.stats.active - this.stats.onLeave);
    this.cdr.detectChanges();
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
    this.docDataMap = {};
    this.docCompletionMap = {};
    this.loadHrDocKpis();
    this.pageSubject.next(1);
    this.searchTrigger$.next(true);
    this.cdr.detectChanges();
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
    this.cdr.detectChanges();
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

  loadHrDocKpis(): void {
    this.documentService.getHrOverview().subscribe({
      next: (kpi) => {
        if (kpi) {
          const total = kpi.total_employees || 0;
          this.stats.total = total;
          this.stats.docCompleteCount = kpi.complete_employees || 0;
          this.stats.docIncompleteCount = kpi.incomplete_employees || 0;
          this.stats.docPartialCount = Math.max(0, total - (this.stats.docCompleteCount + this.stats.docIncompleteCount));
          
          if (total > 0) {
            this.stats.docCompletePct = Math.round((this.stats.docCompleteCount / total) * 100);
            this.stats.docPartialPct = Math.round((this.stats.docPartialCount / total) * 100);
            this.stats.docIncompletePct = Math.max(0, 100 - (this.stats.docCompletePct + this.stats.docPartialPct));
          } else {
            this.stats.docCompletePct = 0;
            this.stats.docPartialPct = 0;
            this.stats.docIncompletePct = 0;
          }
          this.cdr.markForCheck();
          this.cdr.detectChanges();
        }
      },
      error: () => {}
    });
  }

  loadDocumentCompletions(employees: Employee[]): void {
    if (!employees || employees.length === 0) return;
    const reqs = employees
      .filter(emp => !this.docDataMap[String(emp.id)])
      .map(emp =>
        this.documentService.getEmployeeDocumentsForHr(emp.id).pipe(
          tap((res: EmployeeDocumentsPageResponse) => {
            if (res && res.summary) {
              const v = res.summary.verified || 0;
              const u = res.summary.uploaded || 0;
              const tot = res.summary.total_required || 8;
              const pct = res.summary.completion_percentage || 0;
              let label = 'Incomplete';
              let color = '#EF4444';
              if (pct >= 100) {
                label = 'Complete';
                color = '#10B981';
              } else if (pct >= 40 || u > 0) {
                label = 'Partial';
                color = '#F59E0B';
              }

              // Extract real uploaded document icons from items
              const uploadedItems = (res.documents || []).filter((item: EmployeeDocumentItem) => !!item.document_id || !!item.file_name);
              const fileIcons: EmployeeDocFileIcon[] = [];

              uploadedItems.forEach((item: EmployeeDocumentItem) => {
                const fname = (item.file_name || '').toLowerCase();
                const ext = fname.split('.').pop() || '';
                if (ext === 'pdf') {
                  fileIcons.push({ type: 'pdf', title: `${item.document_type_name} (PDF)`, iconClass: 'fas fa-file-pdf' });
                } else if (['jpg', 'jpeg', 'png', 'webp', 'svg'].includes(ext)) {
                  fileIcons.push({ type: 'image', title: `${item.document_type_name} (Image)`, iconClass: 'fas fa-file-image' });
                } else if (['doc', 'docx'].includes(ext)) {
                  fileIcons.push({ type: 'word', title: `${item.document_type_name} (Word)`, iconClass: 'fas fa-file-word' });
                } else if (['xls', 'xlsx', 'csv'].includes(ext)) {
                  fileIcons.push({ type: 'excel', title: `${item.document_type_name} (Spreadsheet)`, iconClass: 'fas fa-file-excel' });
                } else {
                  fileIcons.push({ type: 'other', title: `${item.document_type_name}`, iconClass: 'fas fa-file-alt' });
                }
              });

              const displayIcons = fileIcons.slice(0, 3);
              const extraCount = Math.max(0, fileIcons.length - 3);

              const key = String(emp.id);
              this.docDataMap[key] = {
                uploadedCount: u,
                verifiedCount: v,
                totalRequired: tot,
                completionPct: pct,
                label,
                color,
                fileIcons: displayIcons,
                extraCount
              };
              this.docCompletionMap[key] = { count: v, total: tot, label, color };
            }
          }),
          catchError(() => of(null))
        )
      );

    if (reqs.length > 0) {
      forkJoin(reqs).subscribe({
        next: () => {
          this.cdr.markForCheck();
          this.cdr.detectChanges();
        },
        error: () => {
          this.cdr.markForCheck();
          this.cdr.detectChanges();
        }
      });
    }
  }

  getDocCompletion(emp: Employee): { count: number, total: number, label: string, color: string } {
    const key = String(emp.id);
    if (this.docCompletionMap[key]) {
      return this.docCompletionMap[key];
    }
    return { count: 0, total: 8, label: 'Incomplete', color: '#EF4444' };
  }

  getDocData(emp: Employee): EmployeeDocSummaryInfo {
    const key = String(emp.id);
    if (this.docDataMap[key]) {
      return this.docDataMap[key];
    }
    return {
      uploadedCount: 0,
      verifiedCount: 0,
      totalRequired: 8,
      completionPct: 0,
      label: 'Not Uploaded',
      color: '#94A3B8',
      fileIcons: [],
      extraCount: 0
    };
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

  openViewModal(employee: Employee, tab: 'details' | 'documents' = 'details'): void {
    this.selectedEmployee = employee;
    this.viewModalTab = tab;
    this.activeModal = 'view';
    this.cdr.detectChanges();
  }

  openEditModal(employee: Employee): void {
    this.selectedEmployee = employee;
    this.activeModal = 'edit';
    this.cdr.detectChanges();
  }

  openCredentialModal(employee: Employee): void {
    this.selectedEmployee = employee;
    this.activeModal = 'credential';
    this.cdr.detectChanges();
  }

  openAddModal(): void {
    this.activeModal = 'add';
    this.cdr.detectChanges();
  }

  onModalClose(refresh: boolean = false): void {
    this.activeModal = null;
    this.selectedEmployee = null;
    this.viewModalTab = 'details';
    if (refresh) {
      this.onSearch();
    }
    this.cdr.detectChanges();
  }

  confirmDelete(employee: Employee): void {
    this.employeeToDelete = employee;
    this.deleteModalOpen = true;
    this.cdr.detectChanges();
  }

  closeDeleteModal(): void {
    this.deleteModalOpen = false;
    this.employeeToDelete = null;
    this.cdr.detectChanges();
  }

  executeDelete(): void {
    if (!this.employeeToDelete) return;
    const employee = this.employeeToDelete;
    this.closeDeleteModal();
    this.isLoading$.next(true);
    this.cdr.detectChanges();
    this.employeeService.deleteEmployee(employee.id).subscribe({
      next: () => {
        this.onSearch();
      },
      error: (err) => {
        this.isLoading$.next(false);
        this.cdr.detectChanges();
        console.error('Failed to delete employee:', err);
        alert(err?.error?.detail || 'An error occurred while deleting the employee.');
      }
    });
  }
}
