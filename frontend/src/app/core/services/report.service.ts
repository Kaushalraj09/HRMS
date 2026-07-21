import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import {
  AttendanceSummaryRow,
  LateArrivalRow,
  MissingPunchRow,
  LeaveUsageRow,
  HrWorkloadRow,
  EmployeeStatusRow,
  LoginActivitySummaryRow,
  PaginatedReportResponse
} from '../models/report.model';

@Injectable({
  providedIn: 'root'
})
export class ReportService {
  private readonly apiUrl = buildApiUrl('/reports');

  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
  });

  constructor(private readonly http: HttpClient) {}

  private noCacheParams(): HttpParams {
    return new HttpParams().set('_ts', Date.now().toString());
  }

  // HR Reports
  getAttendanceSummary(
    startDate: string = '',
    endDate: string = '',
    department: string = '',
    search: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<AttendanceSummaryRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);
    if (department) params = params.set('department', department);
    if (search) params = params.set('search', search);

    return this.http.get<PaginatedReportResponse<AttendanceSummaryRow>>(
      `${this.apiUrl}/hr/attendance-summary`,
      { headers: this.noCacheHeaders, params }
    );
  }

  getLateArrivals(
    startDate: string = '',
    endDate: string = '',
    department: string = '',
    search: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<LateArrivalRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);
    if (department) params = params.set('department', department);
    if (search) params = params.set('search', search);

    return this.http.get<PaginatedReportResponse<LateArrivalRow>>(
      `${this.apiUrl}/hr/late-arrivals`,
      { headers: this.noCacheHeaders, params }
    );
  }

  getMissingPunches(
    startDate: string = '',
    endDate: string = '',
    department: string = '',
    search: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<MissingPunchRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);
    if (department) params = params.set('department', department);
    if (search) params = params.set('search', search);

    return this.http.get<PaginatedReportResponse<MissingPunchRow>>(
      `${this.apiUrl}/hr/missing-punches`,
      { headers: this.noCacheHeaders, params }
    );
  }

  getLeaveUsage(
    startDate: string = '',
    endDate: string = '',
    department: string = '',
    search: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<LeaveUsageRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);
    if (department) params = params.set('department', department);
    if (search) params = params.set('search', search);

    return this.http.get<PaginatedReportResponse<LeaveUsageRow>>(
      `${this.apiUrl}/hr/leave-usage`,
      { headers: this.noCacheHeaders, params }
    );
  }

  // Admin Reports
  getHrWorkload(
    startDate: string = '',
    endDate: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<HrWorkloadRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);

    return this.http.get<PaginatedReportResponse<HrWorkloadRow>>(
      `${this.apiUrl}/admin/hr-workload`,
      { headers: this.noCacheHeaders, params }
    );
  }

  getEmployeeStatus(
    department: string = '',
    search: string = '',
    status: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<EmployeeStatusRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (department) params = params.set('department', department);
    if (search) params = params.set('search', search);
    if (status) params = params.set('status', status);

    return this.http.get<PaginatedReportResponse<EmployeeStatusRow>>(
      `${this.apiUrl}/admin/employee-status`,
      { headers: this.noCacheHeaders, params }
    );
  }

  getLoginActivitySummary(
    startDate: string = '',
    endDate: string = '',
    page: number = 1,
    limit: number = 10
  ): Observable<PaginatedReportResponse<LoginActivitySummaryRow>> {
    let params = this.noCacheParams()
      .set('page', page.toString())
      .set('limit', limit.toString());

    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);

    return this.http.get<PaginatedReportResponse<LoginActivitySummaryRow>>(
      `${this.apiUrl}/admin/login-activity`,
      { headers: this.noCacheHeaders, params }
    );
  }

  // General CSV Export
  exportReportCsv(endpointPath: string, filterParams: any): Observable<Blob> {
    let params = new HttpParams().set('export', 'pdf');
    Object.keys(filterParams).forEach(key => {
      if (filterParams[key] !== null && filterParams[key] !== undefined && filterParams[key] !== '') {
        params = params.set(key, filterParams[key].toString());
      }
    });

    return this.http.get(`${this.apiUrl}/${endpointPath}`, {
      params,
      responseType: 'blob'
    });
  }
}
