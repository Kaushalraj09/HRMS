import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map, Subject, switchMap } from 'rxjs';

import { buildApiUrl, buildWsUrl } from '../config/api.config';
import { AttendanceMetrics, AttendanceRecord, EmployeeAttendanceSummaryItem, EmployeeTimesheetRow, PaginatedAttendance, TodayAttendanceState, WorkMode, PaginatedResponse } from '../models/attendance.model';
import { formatMinutesToHours } from '../utils/attendance-calc.util';
import { TimeoffService } from './timeoff.service';
import { environment } from '../../../environments/environment';

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
  metrics: AttendanceMetrics;
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
  yesterdayAutoCheckedOut?: boolean;
  requiresRegularization?: boolean;
  overtimeApproved?: boolean;
  overtimeExtended?: boolean;
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
  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache'
  });
  private socket: WebSocket | null = null;
  private reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
  public get timeoffUpdate$() {
    return this.timeoffService.timeoffUpdate$;
  }
  private wsMessageSubject = new Subject<any>();
  public wsMessage$ = this.wsMessageSubject.asObservable();

  constructor(
    private readonly http: HttpClient,
    private readonly timeoffService: TimeoffService
  ) { }

  connectWebSocket(userId: string | number) {
    const token = localStorage.getItem('aivan_hrms_phase1_token_v1') || '';
    if (!token) {
      console.warn('Skipping WebSocket connection because no auth token is available.');
      return;
    }

    this.clearReconnectTimeout();

    const wsUrl = buildWsUrl(`/ws/${userId}?token=${encodeURIComponent(token)}`);
    
    // If we already have a socket connection to this exact URL, don't reconnect.
    if (this.socket && this.socket.url === wsUrl) {
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

    if (!environment.production) {
      console.log(`Attempting WebSocket connection to: ${wsUrl}`);
    }

    const socket = new WebSocket(wsUrl);
    this.socket = socket;

    socket.onopen = () => {
      if (!environment.production) {
        console.log('WebSocket connection established successfully');
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.wsMessageSubject.next(data);
        if (data.type === 'TIMEOFF_UPDATE' || data.type === 'TIMEOFF_REQUEST') {
          this.timeoffService.triggerTimeOffUpdate(data);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message', e);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    socket.onclose = (event) => {
      if (this.socket === socket) {
        this.socket = null;
      }

      if (event.code === 4001) {
        console.warn('WebSocket authentication failed. Reconnect skipped until the user signs in again.');
        return;
      }

      console.warn(`WebSocket closed: ${event.code} ${event.reason}. Retrying in 5s...`);
      this.reconnectTimeoutId = setTimeout(() => this.connectWebSocket(userId), 5000);
    };
  }

  disconnectWebSocket() {
    this.clearReconnectTimeout();
    if (this.socket) {
      this.socket.onclose = () => { };
      this.socket.onerror = () => { };
      try {
        this.socket.close();
      } catch (e) {}
      this.socket = null;
    }
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
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
    const options = this.noCacheOptions();
    options.params = options.params
      .set('page', page)
      .set('limit', limit)
      .set('search', search.trim())
      .set('department', department)
      .set('status', status)
      .set('location', location || '');
    if (fromDate) {
      options.params = options.params.set('fromDate', fromDate);
    }
    if (toDate) {
      options.params = options.params.set('toDate', toDate);
    }

    return this.http.get<BackendAttendanceListResponse>(`${this.apiUrl}/all`, options).pipe(
      map(result => ({
        data: result.data.map(row => this.mapAttendanceRecord(row)),
        total: result.total,
        metrics: result.metrics
      }))
    );
  }

  getMyTimesheets(fromDate: string = '', toDate: string = '', status: string = ''): Observable<EmployeeTimesheetRow[]> {
    const options = this.noCacheOptions();
    const trimmedStatus = status.trim();
    if (fromDate) {
      options.params = options.params.set('from_date', fromDate);
    }
    if (toDate) {
      options.params = options.params.set('to_date', toDate);
    }
    if (trimmedStatus) {
      options.params = options.params.set('status', trimmedStatus);
    }

    return this.http.get<BackendAttendanceResponse[]>(`${this.apiUrl}/me/timesheets`, options).pipe(
      map(rows => rows.map(row => this.mapTimesheet(row)))
    );
  }

  getTodayAttendanceState(): Observable<TodayAttendanceState> {
    return this.http.get<BackendTodayAttendanceState>(`${this.apiUrl}/me/today`, this.noCacheOptions()).pipe(
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
        punchOutImage: state.punchOutImage,
        yesterdayAutoCheckedOut: state.yesterdayAutoCheckedOut,
        requiresRegularization: state.requiresRegularization,
        overtimeApproved: state.overtimeApproved,
        overtimeExtended: state.overtimeExtended
      }))
    );
  }

  punchIn(workMode: WorkMode, latitude?: number, longitude?: number, address?: string, image?: string | null): Observable<TodayAttendanceState> {
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/me/punch`, {
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
    return this.http.post<BackendAttendanceResponse>(`${this.apiUrl}/me/punch`, {
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

  continueWorking(): Observable<TodayAttendanceState> {
    return this.http.post<void>(`${this.apiUrl}/continue-working`, {}).pipe(
      switchMap(() => this.getTodayAttendanceState())
    );
  }

  extendOvertime(): Observable<TodayAttendanceState> {
    return this.http.post<void>(`${this.apiUrl}/extend-overtime`, {}).pipe(
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



  getMyAttendanceSummary(): Observable<EmployeeAttendanceSummaryItem[]> {
    return this.http.get<EmployeeAttendanceSummaryItem[]>(`${this.apiUrl}/me/summary`, this.noCacheOptions());
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

  private normalizeStatus(status: string): AttendanceRecord['status'] {
    const knownStatuses = ['Present', 'Working', 'Absent', 'Not Marked', 'Half Day', 'Time Off'];
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
