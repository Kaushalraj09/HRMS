import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { buildApiUrl } from '../config/api.config';
import { Employee, PaginatedResult } from '../models/employee.model';
import { TimeOffRequest } from '../models/timeoff.model';

export interface ManagerDashboardStats {
  totalEmployees: number;
  presentToday: number;
  absentToday: number;
  onLeaveToday: number;
  lateToday: number;
  currentlyWorking: number;
  pendingApprovals: number;
  teamOverview?: Array<{
    employeeId: number;
    employeeCode: string;
    name: string;
    department: string;
    designation: string;
    status: string;
    punchIn?: string | null;
    punchOut?: string | null;
  }>;
}

export interface AttendanceTrendData {
  period: string;
  labels: string[];
  present: number[];
  leave: number[];
  absent: number[];
}

@Injectable({
  providedIn: 'root'
})
export class ManagerService {
  private readonly apiUrl = buildApiUrl('/manager');

  constructor(private readonly http: HttpClient) {}

  getDashboardStats(): Observable<ManagerDashboardStats> {
    return this.http.get<ManagerDashboardStats>(`${this.apiUrl}/dashboard-stats`);
  }

  getAttendanceTrend(period: string = 'This Month'): Observable<AttendanceTrendData> {
    return this.http.get<AttendanceTrendData>(`${this.apiUrl}/attendance-trend`, {
      params: { period }
    });
  }

  getTeam(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedResult<Employee>> {
    const params: any = { page, limit };
    if (search && search.trim()) {
      params.search = search.trim();
    }
    return this.http.get<PaginatedResult<Employee>>(`${this.apiUrl}/team`, { params });
  }

  getTeamMember(employeeId: string | number): Observable<Employee> {
    return this.http.get<Employee>(`${this.apiUrl}/team/${employeeId}`);
  }

  getTeamAttendance(params: {
    page?: number;
    limit?: number;
    fromDate?: string;
    toDate?: string;
    employeeId?: number;
    status?: string;
    search?: string;
  }): Observable<any> {
    const queryParams: any = {
      page: params.page || 1,
      limit: params.limit || 10
    };
    if (params.fromDate) queryParams.fromDate = params.fromDate;
    if (params.toDate) queryParams.toDate = params.toDate;
    if (params.employeeId) queryParams.employeeId = params.employeeId;
    if (params.status) queryParams.status = params.status;
    if (params.search) queryParams.search = params.search;

    return this.http.get<any>(`${this.apiUrl}/attendance`, { params: queryParams });
  }

  getTeamLeaveRequests(page: number = 1, pageSize: number = 10, status: string = ''): Observable<{
    items: TimeOffRequest[];
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  }> {
    const params: any = { page, pageSize };
    if (status) params.status = status;
    return this.http.get<any>(`${this.apiUrl}/leave-requests`, { params });
  }

  getLeaveRequestDetail(requestId: number): Observable<TimeOffRequest> {
    return this.http.get<TimeOffRequest>(`${this.apiUrl}/leave-requests/${requestId}`);
  }

  approveLeaveRequest(requestId: number, comment?: string): Observable<TimeOffRequest> {
    return this.http.post<TimeOffRequest>(`${this.apiUrl}/leave-requests/${requestId}/approve`, {
      comment: comment || ''
    });
  }

  rejectLeaveRequest(requestId: number, comment: string): Observable<TimeOffRequest> {
    return this.http.post<TimeOffRequest>(`${this.apiUrl}/leave-requests/${requestId}/reject`, {
      comment
    });
  }
}
