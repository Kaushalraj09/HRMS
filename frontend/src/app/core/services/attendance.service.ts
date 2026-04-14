import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { AttendanceRecord, EmployeeAttendanceSummaryItem, EmployeeTimesheetRow, PaginatedAttendance, TodayAttendanceState, WorkMode } from '../models/attendance.model';

import { Phase1StoreService } from './phase1-store.service';

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  constructor(private readonly store: Phase1StoreService) {}

  getAttendanceLogs(
    page: number, 
    limit: number, 
    fromDate: string, 
    toDate: string, 
    search: string, 
    department: string, 
    status: string
  ): Observable<PaginatedAttendance> {
    return of(this.store.listAttendance({ page, limit, fromDate, toDate, search, department, status }).result).pipe(delay(300));
  }

  getMyTimesheets(): Observable<EmployeeTimesheetRow[]> {
    return of(this.store.getMyTimesheets()).pipe(delay(200));
  }

  getTodayAttendanceState(): Observable<TodayAttendanceState> {
    return of(this.store.getTodayAttendanceState()).pipe(delay(150));
  }

  toggleMyPunch(workMode: WorkMode): Observable<TodayAttendanceState> {
    return of(this.store.toggleMyPunch(workMode)).pipe(delay(250));
  }

  getMyAttendanceSummary(): Observable<EmployeeAttendanceSummaryItem[]> {
    return of(this.store.getAttendanceSummaryItems()).pipe(delay(150));
  }
}
