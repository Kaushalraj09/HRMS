import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Observable, BehaviorSubject, combineLatest } from 'rxjs';
import { switchMap, tap, map, shareReplay } from 'rxjs/operators';
import { Employee, PaginatedResult } from '../../../../core/models/employee.model';
import { EmployeeService } from '../../../../core/services/employee.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-employees',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CustomSelectComponent, RouterModule],
  templateUrl: './employees.html',
  styleUrl: './employees.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class Employees implements OnInit {
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
  userRoleLabel = 'HR';

  constructor(private employeeService: EmployeeService, private readonly authService: AuthService) {}

  ngOnInit(): void {
    this.userRoleLabel = this.authService.getCurrentUser()?.role === 'admin' ? 'Admin' : 'HR';
    this.employeesData$ = combineLatest([
      this.searchTrigger$,
      this.pageSubject.asObservable()
    ]).pipe(
      tap(() => this.isLoading$.next(true)),
      switchMap(([_, page]) => {
        return this.employeeService.getEmployees(
             page, 
             this.pageSize, 
             this.searchControl.value || '', 
             this.departmentControl.value || '', 
             this.typeControl.value || '', 
             this.statusControl.value || ''
        );
      }),
      tap(() => this.isLoading$.next(false)),
      shareReplay(1)
    );

    this.paginationArray$ = this.employeesData$.pipe(
      map(res => {
        const totalPages = Math.ceil(res.total / this.pageSize);
        return Array.from({length: totalPages}, (_, i) => i + 1);
      })
    );
  }

  setPage(page: number) {
    this.pageSubject.next(page);
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

  trackById(index: number, employee: Employee): string {
    return employee.id;
  }
}
