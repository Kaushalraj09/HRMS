import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map, Subject, switchMap } from 'rxjs';

import { AttendanceMetrics, AttendanceRecord, EmployeeAttendanceSummaryItem, EmployeeTimesheetRow, PaginatedAttendance, TodayAttendanceState, WorkMode } from '../models/attendance.model';

interface BackendAttendanceResponse {
  id: number;
  date: string;
  scheduledStart: string | null;
  scheduledEnd: string | null;
  taskDescription: string | null;
  checkIn: string | null;
  checkOut: string | null;
  status: string;
  workMode: WorkMode;
  totalWorkingMinutes: number;
  overtimeMinutes: number;
  breakMinutes: number;
  grandTotalMinutes: number;
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
  totalWorkingMinutes: number;
}

interface BackendAttendanceListResponse {
  data: BackendAttendanceRecord[];
  total: number;
}

interface BackendTodayAttendanceState {
  isWorking: boolean;
  status: string;
  totalWorkedSeconds: number;
  approvedSeconds: number;
  remainingSeconds: number;
  shiftTotalSeconds: number;
  shiftElapsedSeconds: number;
  shiftStart: string;
  shiftEnd: string;
  workMode: WorkMode;
  checkIn: string | null;
  checkOut: string | null;
}

export interface TimeOffApplyResponse {
  id: number;
  employee_id: number;
  date: string;
  leave_type: string;
  start_time: string | null;
  end_time: string | null;
  duration_hours: number;
  status: string;
  approved_hours_today: number;
  remaining_hours_today: number;
  approved_seconds_today: number;
  remaining_seconds_today: number;
}

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/attendance';
  private readonly timeoffApiUrl = 'http://localhost:8000/api/v1/timeoff';
  private socket: WebSocket | null = null;
  private timeoffUpdateSubject = new Subject<any>();
  public timeoffUpdate$ = this.timeoffUpdateSubject.asObservable();

  constructor(private readonly http: HttpClient) {}

  connectWebSocket(userId: string | number) {
    if (this.socket) {
      this.socket.close();
    }
    this.socket = new WebSocket(`ws://localhost:8000/ws/${userId}`);
    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'TIMEOFF_UPDATE') {
          this.timeoffUpdateSubject.next(data);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message', e);
      }
    };
  }

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
    return this.http.get<BackendTodayAttendanceState>(`${this.apiUrl}/today`).pipe(
      map(state => ({
        isWorking: state.isWorking,
        status: state.status,
        totalWorkedSeconds: Number(state.totalWorkedSeconds) || 0,
        approvedSeconds: Number(state.approvedSeconds) || 0,
        remainingSeconds: Number(state.remainingSeconds) || 0,
        shiftTotalSeconds: Number(state.shiftTotalSeconds) || 0,
        shiftElapsedSeconds: Number(state.shiftElapsedSeconds) || 0,
        shiftStart: state.shiftStart,
        shiftEnd: state.shiftEnd,
        workMode: state.workMode || 'Office',
        checkIn: state.checkIn,
        checkOut: state.checkOut
      }))
    );
  }

  punchIn(workMode: WorkMode): Observable<TodayAttendanceState> {
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/punch-in`, { workMode }).pipe(
      switchMap(() => this.getTodayAttendanceState())
    );
  }

  punchOut(workMode: WorkMode): Observable<TodayAttendanceState> {
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/punch-out`, { workMode }).pipe(
      switchMap(() => this.getTodayAttendanceState())
    );
  }

  addSchedule(
    date: string,
    workMode: WorkMode,
    taskDescription: string,
    startTime?: string,
    endTime?: string
  ): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/schedule`, {
      date,
      workMode,
      taskDescription,
      startTime: startTime || null,
      endTime: endTime || null
    });
  }

  requestTimeOff(
    date: string,
    leaveType: string,
    startTime: string | null,
    endTime: string | null,
    durationHours: number
  ): Observable<any> {
    return this.http.post(`${this.timeoffApiUrl}/request`, {
      date,
      leave_type: leaveType,
      start_time: startTime,
      end_time: endTime,
      duration_hours: durationHours
    });
  }

  /** Inline card: POST /api/v1/timeoff/apply */
  applyTimeOffInline(payload: {
    date: string;
    leave_type: string;
    start_time: string | null;
    end_time: string | null;
  }): Observable<TimeOffApplyResponse> {
    return this.http.post<TimeOffApplyResponse>(`${this.timeoffApiUrl}/apply`, {
      date: payload.date,
      leave_type: payload.leave_type,
      start_time: payload.start_time,
      end_time: payload.end_time
    });
  }

  getPendingTimeOffRequests(): Observable<any[]> {
    return this.http.get<any[]>(`${this.timeoffApiUrl}/pending`);
  }

  approveTimeOffRequest(requestId: number, action: string, approvedHours?: number, comments?: string): Observable<any> {
    let params = `?action=${action}`;
    if (approvedHours !== undefined) params += `&approved_duration_hours=${approvedHours}`;
    if (comments) params += `&comments=${encodeURIComponent(comments)}`;
    return this.http.put(`${this.timeoffApiUrl}/approve/${requestId}${params}`, {});
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
      hours: this.formatMinutes(row.totalWorkingMinutes ?? this.calculateMinutes(row.checkIn, row.checkOut)),
      status: this.normalizeStatus(row.status)
    };
  }

  private mapTimesheet(row: BackendAttendanceResponse): EmployeeTimesheetRow {
    const displayCheckIn = this.toDisplayTime(row.checkIn);
    const displayCheckOut = this.toDisplayTime(row.checkOut);
    const displayScheduledStart = this.toDisplayTime(row.scheduledStart);
    const displayScheduledEnd = this.toDisplayTime(row.scheduledEnd);
    const workMinutes = row.totalWorkingMinutes ?? this.calculateMinutes(row.checkIn, row.checkOut);

    return {
      date: row.date,
      day: new Date(row.date).toLocaleDateString('en-US', { weekday: 'short' }),
      scheduledStart: displayScheduledStart || undefined,
      scheduledEnd: displayScheduledEnd || undefined,
      taskDescription: row.taskDescription || undefined,
      // For schedule-only rows (future/pending), show scheduled times in the timesheet table.
      entry: displayCheckIn || displayScheduledStart || '-',
      exit: displayCheckOut || displayScheduledEnd || '-',
      total: this.formatMinutes(workMinutes),
      overtime: this.formatMinutes(row.overtimeMinutes ?? 0),
      break: this.formatMinutes(row.breakMinutes ?? 0),
      grandTotal: this.formatMinutes(row.grandTotalMinutes ?? workMinutes),
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
    if (status === 'Checked In' || status === 'Checked Out' || status === 'Not Marked' || status === 'Present' || status === 'Working' || status === 'Not working') {
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
