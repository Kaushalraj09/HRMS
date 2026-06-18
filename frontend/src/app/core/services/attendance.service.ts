import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map, Subject, switchMap } from 'rxjs';

import { buildApiUrl, buildWsUrl } from '../config/api.config';
import { AttendanceMetrics, AttendanceRecord, EmployeeAttendanceSummaryItem, EmployeeTimesheetRow, PaginatedAttendance, TodayAttendanceState, WorkMode } from '../models/attendance.model';
import { formatMinutesToHours } from '../utils/attendance-calc.util';

interface BackendAttendanceResponse {
  id: number;
  employeeId: number;
  date: string;
  scheduledStart: string | null;
  scheduledEnd: string | null;
  taskDescription: string | null;
  punchIn: string | null;
  punchOut: string | null;
  status: string;
  workMode: WorkMode;
  totalWorkingMinutes: number;
  overtimeMinutes: number;
  breakMinutes: number;
  grandTotalMinutes: number;
  lateMinutes: number;
}

interface BackendAttendanceRecord {
  id: number;
  employeeName: string;
  employeeCode: string;
  department: string;
  date: string;
  punchIn: string | null;
  punchOut: string | null;
  status: string;
  totalWorkingMinutes: number;
  workMode?: string;
  punchInAddress?: string;
  punchOutAddress?: string;
  punchInImage?: string;
  punchOutImage?: string;
}

interface BackendAttendanceListResponse {
  data: BackendAttendanceRecord[];
  total: number;
}

interface BackendTodayAttendanceState {
  employeeId: number | null;
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
  punchIn: string | null;
  punchOut: string | null;
  punchInLatitude: number | null;
  punchInLongitude: number | null;
  punchInAddress: string | null;
  punchOutLatitude: number | null;
  punchOutLongitude: string | null; // Keep flexible type mapping
  punchOutAddress: string | null;
  punchInImage: string | null;
  punchOutImage: string | null;
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
  private readonly apiUrl = buildApiUrl('/attendance');
  private readonly timeoffApiUrl = buildApiUrl('/timeoff');
  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache'
  });
  private socket: WebSocket | null = null;
  private timeoffUpdateSubject = new Subject<any>();
  public timeoffUpdate$ = this.timeoffUpdateSubject.asObservable();
  private wsMessageSubject = new Subject<any>();
  public wsMessage$ = this.wsMessageSubject.asObservable();

  constructor(private readonly http: HttpClient) { }

  connectWebSocket(userId: string | number) {
    const wsUrl = buildWsUrl(`/ws/${userId}`);
    
    // If we already have a socket connection to this exact URL, don't reconnect
    if (this.socket && (this.socket.url === wsUrl || this.socket.url.endsWith(`/ws/${userId}`))) {
      if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
        return;
      }
    }

    if (this.socket) {
      this.socket.onclose = () => { };
      this.socket.onerror = () => { };
      try {
        this.socket.close();
      } catch (e) {}
    }

    console.log(`Attempting WebSocket connection to: ${wsUrl}`);

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connection established successfully');
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.wsMessageSubject.next(data);
        if (data.type === 'TIMEOFF_UPDATE' || data.type === 'TIMEOFF_REQUEST') {
          this.timeoffUpdateSubject.next(data);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message', e);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    this.socket.onclose = (event) => {
      console.warn(`WebSocket closed: ${event.code} ${event.reason}. Retrying in 5s...`);
      setTimeout(() => this.connectWebSocket(userId), 5000);
    };
  }

  disconnectWebSocket() {
    if (this.socket) {
      this.socket.onclose = () => { };
      this.socket.onerror = () => { };
      try {
        this.socket.close();
      } catch (e) {}
      this.socket = null;
    }
  }

  reverseGeocode(lat: number, lon: number): Observable<any> {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`;
    return this.http.get(url);
  }

  getIpLocation(): Observable<any> {
    return this.http.get(`${this.apiUrl}/ip-location`, this.noCacheOptions());
  }

  getAttendanceLogs(
    page: number,
    limit: number,
    fromDate: string,
    toDate: string,
    search: string,
    department: string,
    status: string,
    location?: string
  ): Observable<PaginatedAttendance> {
    return this.http.get<BackendAttendanceListResponse>(`${this.apiUrl}/all`, this.noCacheOptions()).pipe(
      map(result => {
        let rows = result.data.map(row => this.mapAttendanceRecord(row));
        rows = this.filterAttendanceRows(rows, fromDate, toDate, search, department, status, location);

        // Sort all rows: date descending first, then punch-in time descending (latest first)
        rows.sort((a, b) => {
          const dateDiff = new Date(b.date).getTime() - new Date(a.date).getTime();
          if (dateDiff !== 0) return dateDiff;

          if (a.punchIn && b.punchIn) {
            return b.punchIn.localeCompare(a.punchIn);
          }
          if (b.punchIn) return 1;
          if (a.punchIn) return -1;
          return 0;
        });

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
    return this.http.get<BackendAttendanceResponse[]>(`${this.apiUrl}/my-history`, this.noCacheOptions()).pipe(
      map(rows => rows.map(row => this.mapTimesheet(row)))
    );
  }

  getTodayAttendanceState(): Observable<TodayAttendanceState> {
    return this.http.get<BackendTodayAttendanceState>(`${this.apiUrl}/today`, this.noCacheOptions()).pipe(
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
        punchIn: state.punchIn ?? null,
        punchOut: state.punchOut ?? null,
        punchInLatitude: state.punchInLatitude,
        punchInLongitude: state.punchInLongitude,
        punchInAddress: state.punchInAddress,
        punchOutLatitude: state.punchOutLatitude,
        punchOutLongitude: typeof state.punchOutLongitude === 'string' ? null : state.punchOutLongitude, // Safeguard against DB migration types
        punchOutAddress: state.punchOutAddress,
        punchInImage: state.punchInImage,
        punchOutImage: state.punchOutImage
      }))
    );
  }

  punchIn(workMode: WorkMode, latitude?: number, longitude?: number, address?: string, image?: string | null): Observable<TodayAttendanceState> {
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/punch-in`, {
      workMode,
      latitude,
      longitude,
      address,
      image: image || null
    }).pipe(
      switchMap(() => this.getTodayAttendanceState())
    );
  }

  punchOut(workMode: WorkMode, latitude?: number, longitude?: number, address?: string, image?: string | null): Observable<TodayAttendanceState> {
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/punch-out`, {
      workMode,
      latitude,
      longitude,
      address,
      image: image || null
    }).pipe(
      switchMap(() => this.getTodayAttendanceState())
    );
  }

  updateWorkMode(workMode: WorkMode): Observable<TodayAttendanceState> {
    return this.http.post<TodayAttendanceState>(`${this.apiUrl}/work-mode`, {
      workMode
    });
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

  getMyTimeOffRequests(): Observable<any[]> {
    return this.http.get<any[]>(`${this.timeoffApiUrl}/my-requests`);
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

  getProcessedTimeOffRequests(): Observable<any[]> {
    return this.http.get<any[]>(`${this.timeoffApiUrl}/history`);
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
        { label: 'Present', value: rows.filter(row => row.status === 'Present').length, icon: 'fas fa-check-circle blue-icon' },
        { label: 'Working', value: rows.filter(row => row.status === 'Working').length, icon: 'fas fa-user-check blue-icon' },
        { label: 'Absent', value: rows.filter(row => row.status === 'Absent').length, icon: 'fas fa-times-circle red-icon' },
        { label: 'Not Marked', value: rows.filter(row => row.status === 'Not Marked').length, icon: 'fas fa-user-times unapproved gold-icon' }
      ])
    );
  }

  private mapAttendanceRecord(row: BackendAttendanceRecord): AttendanceRecord {
    const punchIn = row.punchIn ?? null;
    const punchOut = row.punchOut ?? null;

    return {
      id: String(row.id),
      code: row.employeeCode,
      name: row.employeeName,
      department: row.department || '',
      date: row.date,
      punchIn: this.toDisplayTime(punchIn),
      punchOut: this.toDisplayTime(punchOut),
      hours: formatMinutesToHours(row.totalWorkingMinutes ?? this.calculateMinutes(punchIn, punchOut)),
      status: this.normalizeStatus(row.status),
      workMode: row.workMode,
      punchInAddress: row.punchInAddress || '',
      punchOutAddress: row.punchOutAddress || '',
      punchInImage: row.punchInImage,
      punchOutImage: row.punchOutImage
    };
  }

  private noCacheOptions(): { headers: HttpHeaders; params: HttpParams } {
    return {
      headers: this.noCacheHeaders,
      params: new HttpParams().set('_ts', Date.now().toString())
    };
  }

  private mapTimesheet(row: BackendAttendanceResponse): EmployeeTimesheetRow {
    const punchIn = row.punchIn ?? null;
    const punchOut = row.punchOut ?? null;
    const displayPunchIn = this.toDisplayTime(punchIn);
    const displayPunchOut = this.toDisplayTime(punchOut);
    const displayScheduledStart = this.toDisplayTime(row.scheduledStart);
    const displayScheduledEnd = this.toDisplayTime(row.scheduledEnd);
    const workMinutes = Number(row.totalWorkingMinutes) || 0;
    const overtimeMinutes = Number(row.overtimeMinutes) || 0;
    const breakMinutes = Number(row.breakMinutes) || 0;
    const grandTotalMinutes = Number(row.grandTotalMinutes) || 0;

    return {
      date: row.date,
      day: new Date(row.date).toLocaleDateString('en-US', { weekday: 'short' }),
      scheduledStart: displayScheduledStart || undefined,
      scheduledEnd: displayScheduledEnd || undefined,
      taskDescription: row.taskDescription || undefined,
      entry: displayPunchIn || displayScheduledStart || '-',
      exit: displayPunchOut || displayScheduledEnd || '-',
      late: punchIn ? formatMinutesToHours(row.lateMinutes ?? 0) : '-',
      total: punchOut ? formatMinutesToHours(workMinutes) : '-',
      overtime: punchOut ? formatMinutesToHours(overtimeMinutes) : '-',
      break: punchOut ? formatMinutesToHours(breakMinutes) : '-',
      grandTotal: punchOut ? formatMinutesToHours(grandTotalMinutes || workMinutes) : '-',
      status: this.normalizeStatus(row.status)
    };
  }

  private filterAttendanceRows(
    rows: AttendanceRecord[],
    fromDate: string,
    toDate: string,
    search: string,
    department: string,
    status: string,
    location?: string
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
      const matchesLocation = !location || row.workMode === location;

      return matchesFrom && matchesTo && matchesSearch && matchesDepartment && matchesStatus && matchesLocation;
    });
  }

  private buildMetrics(rows: AttendanceRecord[]): AttendanceMetrics {
    return {
      present: rows.filter(row => row.status === 'Present').length,
      working: rows.filter(row => row.status === 'Working').length,
      absent: rows.filter(row => row.status === 'Absent').length,
      notMarked: rows.filter(row => row.status === 'Not Marked').length
    };
  }

  private normalizeStatus(status: string): AttendanceRecord['status'] {
    const knownStatuses = ['Present', 'Working', 'Absent', 'Not Marked'];
    if (knownStatuses.includes(status)) {
      return status as AttendanceRecord['status'];
    }
    if (status === 'Punched In') return 'Working';
    if (status === 'Punched Out' || status === 'Not Working') return 'Present';
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
