import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Observable, BehaviorSubject, combineLatest, of, timer } from 'rxjs';
import { catchError, finalize, map, shareReplay, switchMap, tap } from 'rxjs/operators';
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

  departments = ['Engineering', 'Human Resources', 'Finance', 'Marketing', 'Sales', 'Support'];
  statuses = ['Working', 'Present', 'Absent', 'Not Marked'];
  locations = ['Office', 'Remote'];

  get departmentsOptions() { return [{label: 'All Departments', value: ''}, ...this.departments.map(d => ({label: d, value: d}))]; }
  get statusOptions() { return [{label: 'All Statuses', value: ''}, ...this.statuses.map(s => ({label: s, value: s}))]; }
  get locationOptions() { return [{label: 'All Locations', value: ''}, ...this.locations.map(l => ({label: l, value: l}))]; }

  // BehaviorSubjects to trigger explicit reload instead of debounce
  searchTrigger$ = new BehaviorSubject<boolean>(true);
  pageSubject = new BehaviorSubject<number>(1);
  pageSize = 10;
  
  isLoading$ = new BehaviorSubject<boolean>(true);
  errorMessage$ = new BehaviorSubject<string>('');
  
  attendanceData$!: Observable<PaginatedAttendance>;
  paginationArray$!: Observable<number[]>;

  // Drives the SVG ring: last-loaded metrics snapshot
  lastMetrics: { present: number; working: number; absent: number; notMarked: number } | null = null;

  // Real time indicator bonus
  currentTime$ = timer(0, 60000).pipe(map(() => new Date()));

  // Photo viewer modal state
  selectedPhotoUrl: string | null = null;
  selectedPhotoEmployeeName: string = '';

  openPhotoModal(url: string, employeeName: string): void {
    this.selectedPhotoUrl = url;
    this.selectedPhotoEmployeeName = employeeName;
  }

  closePhotoModal(): void {
    this.selectedPhotoUrl = null;
    this.selectedPhotoEmployeeName = '';
  }

  constructor(private fb: FormBuilder, private attendanceService: AttendanceService) {
    this.filterForm = this.fb.group({
      fromDate: [''],
      toDate: [''],
      employeeSearch: [''],
      department: [''],
      status: [''],
      location: ['']
    });
  }

  /** Fraction 0–1 of employees who are present/working out of the total visible. */
  get attendanceRate(): number {
    if (!this.lastMetrics) return 0;
    const { present, working, absent, notMarked } = this.lastMetrics;
    const total = present + working + absent + notMarked;
    if (total === 0) return 0;
    return Math.min(1, (present + working) / total);
  }

  /** Maps attendanceRate → SVG stroke-dashoffset (pathLength=100 ring). */
  get ringDashOffset(): number {
    return 100 - Math.round(this.attendanceRate * 100);
  }

  ngOnInit(): void {
    
    this.attendanceData$ = combineLatest([
      this.searchTrigger$,
      this.pageSubject.asObservable()
    ]).pipe(
      tap(() => {
        this.errorMessage$.next('');
        this.isLoading$.next(true);
      }),
      switchMap(([_, page]) => {
        const filters = this.filterForm.value;
       return this.attendanceService
          .getAttendanceLogs(
            page,
            this.pageSize,
            filters.fromDate || '',
            filters.toDate || '',
            filters.employeeSearch || '',
            filters.department || '',
            filters.status || '',
            filters.location || '',
          )
         .pipe(
           map((res) => {
             const sorted = [...res.data].sort((a, b) => {
               const dateDiff = new Date(b.date).getTime() - new Date(a.date).getTime();
               if (dateDiff !== 0) return dateDiff;
               if (a.punchIn && b.punchIn) return b.punchIn.localeCompare(a.punchIn);
               if (b.punchIn) return 1;
               if (a.punchIn) return -1;
               return 0;
             });
             // Snapshot metrics for the ring
             this.lastMetrics = res.metrics;
             return { ...res, data: sorted };
           }),
           catchError((error) => {
             const detail = error?.error?.detail;
             this.lastMetrics = { present: 0, working: 0, absent: 0, notMarked: 0 };
             this.errorMessage$.next(typeof detail === 'string' ? detail : 'Unable to load attendance records.');
             return of({
               data: [],
               total: 0,
               metrics: this.lastMetrics
             });
           }),
           finalize(() => this.isLoading$.next(false)),
         );
      }),
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
      status: '',
      location: ''
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
