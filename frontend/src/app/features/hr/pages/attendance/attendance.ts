import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Observable, BehaviorSubject, combineLatest, timer } from 'rxjs';
import { switchMap, tap, map, shareReplay } from 'rxjs/operators';
import { AttendanceRecord, PaginatedAttendance } from '../../../../core/models/attendance.model';
import { AttendanceService } from '../../../../core/services/attendance.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-attendance',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CustomSelectComponent],
  templateUrl: './attendance.html',
  styleUrl: './attendance.css',
  changeDetection: ChangeDetectionStrategy.OnPush, // Force IDE cache refresh
})
export class AttendanceComponent implements OnInit {
  filterForm!: FormGroup;

  departments = ['Engineering', 'HR', 'Finance', 'Marketing', 'Sales', 'Support'];
  statuses = ['Present', 'Checked In', 'Not Marked', 'Checked Out'];

  get departmentsOptions() { return [{label: 'All Departments', value: ''}, ...this.departments.map(d => ({label: d, value: d}))]; }
  get statusOptions() { return [{label: 'All Statuses', value: ''}, ...this.statuses.map(s => ({label: s, value: s}))]; }

  // BehaviorSubjects to trigger explicit reload instead of debounce
  searchTrigger$ = new BehaviorSubject<boolean>(true);
  pageSubject = new BehaviorSubject<number>(1);
  pageSize = 10;
  
  isLoading$ = new BehaviorSubject<boolean>(true);
  
  attendanceData$!: Observable<PaginatedAttendance>;
  paginationArray$!: Observable<number[]>;
  
  // Real time indicator bonus
  currentTime$ = timer(0, 60000).pipe(map(() => new Date()));

  constructor(private fb: FormBuilder, private attendanceService: AttendanceService) {
    this.filterForm = this.fb.group({
      fromDate: [''],
      toDate: [''],
      employeeSearch: [''],
      department: [''],
      status: ['']
    });
  }

  ngOnInit(): void {
    
    this.attendanceData$ = combineLatest([
      this.searchTrigger$,
      this.pageSubject.asObservable()
    ]).pipe(
      tap(() => this.isLoading$.next(true)),
      switchMap(([_, page]) => {
        const filters = this.filterForm.value;
        return this.attendanceService.getAttendanceLogs(
            page, 
            this.pageSize,
            filters.fromDate || '',
            filters.toDate || '',
            filters.employeeSearch || '',
            filters.department || '',
            filters.status || ''
        );
      }),
      tap(() => this.isLoading$.next(false)),
      shareReplay(1)
    );

    this.paginationArray$ = this.attendanceData$.pipe(
      map(res => {
        const totalPages = Math.ceil(res.total / this.pageSize);
        return Array.from({length: totalPages}, (_, i) => i + 1);
      })
    );
  }

  onSearch() {
    this.pageSubject.next(1); // Force to page 1
    this.searchTrigger$.next(true); // Fire pipeline securely
  }

  onReset() {
    this.filterForm.reset({
      fromDate: '',
      toDate: '',
      employeeSearch: '',
      department: '',
      status: ''
    });
    this.onSearch(); // Explicitly trigger the rebuild with empty flags
  }

  setPage(page: number) {
    this.pageSubject.next(page);
  }

  trackById(index: number, record: AttendanceRecord): string {
    return record.id;
  }
}
