import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { AttendanceMetrics, AttendanceRecord, EmployeeAttendanceSummaryItem, EmployeeTimesheetRow, PaginatedAttendance, TodayAttendanceState, WorkMode } from '../models/attendance.model';

interface BackendAttendanceResponse {
  id: number;
  date: string;
  checkIn: string | null;
  checkOut: string | null;
  status: string;
  workMode: WorkMode;
}

interface BackendAttendanceRecord {
  id: number;
  employeeName: string;
  employeeCode: string;
  department: string;
  date: string;
  checkIn: string | null;
  checkOut: string | null;
  status: string;
}

interface BackendAttendanceListResponse {
  data: BackendAttendanceRecord[];
  total: number;
}

interface BackendTodayAttendanceState {
  isPunchedIn: boolean;
  status: string;
  checkIn: string | null;
  checkOut: string | null;
  workMode: WorkMode;
}

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/attendance';

  constructor(private readonly http: HttpClient) {}

  getAttendanceLogs(
    page: number,
    limit: number,
    fromDate: string,
    toDate: string,
    search: string,
    department: string,
    status: string
  ): Observable<PaginatedAttendance> {
    return this.http.get<BackendAttendanceListResponse>(`${this.apiUrl}/all`).pipe(
      map(result => {
        let rows = result.data.map(row => this.mapAttendanceRecord(row));
        rows = this.filterAttendanceRows(rows, fromDate, toDate, search, department, status);
        const metrics = this.buildMetrics(rows);
        const startIndex = (page - 1) * limit;

        return {
          data: rows.slice(startIndex, startIndex + limit),
          total: rows.length,
          metrics
        };
      })
    );
  }

  getMyTimesheets(): Observable<EmployeeTimesheetRow[]> {
    return this.http.get<BackendAttendanceResponse[]>(`${this.apiUrl}/my-history`).pipe(
      map(rows => rows.map(row => this.mapTimesheet(row)))
    );
  }

  getTodayAttendanceState(): Observable<TodayAttendanceState> {
    return this.http.get<BackendTodayAttendanceState>(`${this.apiUrl}/today-state`).pipe(
      map(state => ({
        isPunchedIn: state.isPunchedIn,
        status: this.normalizeStatus(state.status),
        approvedHours: 2,
        remainingHours: 8,
        workMode: state.workMode || 'Office'
      }))
    );
  }

  toggleMyPunch(workMode: WorkMode): Observable<TodayAttendanceState> {
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/toggle`, { workMode }).pipe(
      map(record => ({
        isPunchedIn: !record.checkOut,
        status: this.normalizeStatus(record.status),
        approvedHours: 2,
        remainingHours: 8,
        workMode: record.workMode || workMode
      }))
    );
  }

  getMyAttendanceSummary(): Observable<EmployeeAttendanceSummaryItem[]> {
    return this.getMyTimesheets().pipe(
      map(rows => [
        { label: 'Total Days', value: rows.length, icon: 'fas fa-calendar total blue-icon' },
        { label: 'Worked Days', value: rows.filter(row => row.status !== 'Not Marked').length, icon: 'fas fa-calendar-check worked blue-icon' },
        { label: 'Present', value: rows.filter(row => row.status === 'Present' || row.status === 'Checked Out').length, icon: 'fas fa-check-circle blue-icon' },
        { label: 'Checked In', value: rows.filter(row => row.status === 'Checked In').length, icon: 'fas fa-user-check blue-icon' },
        { label: 'Not Marked', value: rows.filter(row => row.status === 'Not Marked').length, icon: 'fas fa-user-times unapproved blue-icon' }
      ])
    );
  }

  private mapAttendanceRecord(row: BackendAttendanceRecord): AttendanceRecord {
    return {
      id: String(row.id),
      code: row.employeeCode,
      name: row.employeeName,
      department: row.department || '',
      date: row.date,
      checkIn: this.toDisplayTime(row.checkIn),
      checkOut: this.toDisplayTime(row.checkOut),
      hours: this.formatHoursFromTimes(row.checkIn, row.checkOut),
      status: this.normalizeStatus(row.status)
    };
  }

  private mapTimesheet(row: BackendAttendanceResponse): EmployeeTimesheetRow {
    const workMinutes = this.calculateMinutes(row.checkIn, row.checkOut);
    return {
      date: row.date,
      day: new Date(row.date).toLocaleDateString('en-US', { weekday: 'short' }),
      entry: this.toDisplayTime(row.checkIn) || '-',
      exit: this.toDisplayTime(row.checkOut) || '-',
      total: this.formatMinutes(workMinutes),
      overtime: '0h 0m',
      break: '0h 0m',
      grandTotal: this.formatMinutes(workMinutes),
      status: this.normalizeStatus(row.status)
    };
  }

  private filterAttendanceRows(
    rows: AttendanceRecord[],
    fromDate: string,
    toDate: string,
    search: string,
    department: string,
    status: string
  ): AttendanceRecord[] {
    const searchValue = search.trim().toLowerCase();

    return rows.filter(row => {
      const matchesFrom = !fromDate || row.date >= fromDate;
      const matchesTo = !toDate || row.date <= toDate;
      const matchesSearch = !searchValue
        || row.name.toLowerCase().includes(searchValue)
        || row.code.toLowerCase().includes(searchValue);
      const matchesDepartment = !department || row.department === department;
      const normalizedStatus = this.normalizeStatus(status || '');
      const matchesStatus = !status || row.status === normalizedStatus;

      return matchesFrom && matchesTo && matchesSearch && matchesDepartment && matchesStatus;
    });
  }

  private buildMetrics(rows: AttendanceRecord[]): AttendanceMetrics {
    return {
      present: rows.filter(row => row.status === 'Present').length,
      checkedIn: rows.filter(row => row.status === 'Checked In').length,
      checkedOut: rows.filter(row => row.status === 'Checked Out').length,
      notMarked: rows.filter(row => row.status === 'Not Marked').length
    };
  }

  private normalizeStatus(status: string): AttendanceRecord['status'] {
    if (status === 'Checked In' || status === 'Checked Out' || status === 'Not Marked' || status === 'Present') {
      return status;
    }
    return 'Present';
  }

  private toDisplayTime(value: string | null): string {
    if (!value) {
      return '';
    }

    const [hours = '00', minutes = '00'] = value.split(':');
    return `${hours}:${minutes}`;
  }

  private calculateMinutes(checkIn: string | null, checkOut: string | null): number {
    if (!checkIn || !checkOut) {
      return 0;
    }

    const [inHour, inMinute] = checkIn.split(':').map(part => Number(part));
    const [outHour, outMinute] = checkOut.split(':').map(part => Number(part));
    return Math.max(0, (outHour * 60 + outMinute) - (inHour * 60 + inMinute));
  }

  private formatHoursFromTimes(checkIn: string | null, checkOut: string | null): string {
    return this.formatMinutes(this.calculateMinutes(checkIn, checkOut));
  }

  private formatMinutes(minutes: number): string {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hrs}h ${mins}m`;
  }
}
