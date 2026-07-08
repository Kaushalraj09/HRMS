import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { TimeOffRequest, TimeOffApplyResponse } from '../models/timeoff.model';
import { PaginatedResponse } from '../models/attendance.model';

@Injectable({
  providedIn: 'root'
})
export class TimeoffService {
  private readonly apiUrl = buildApiUrl('/timeoff');
  
  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
  });

  private timeoffUpdateSubject = new Subject<any>();
  public timeoffUpdate$ = this.timeoffUpdateSubject.asObservable();

  constructor(private readonly http: HttpClient) {}

  getMyTimeOffRequests(page: number = 1, pageSize: number = 10): Observable<PaginatedResponse<TimeOffRequest>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('pageSize', pageSize.toString())
      .set('_ts', Date.now().toString());
    return this.http.get<PaginatedResponse<TimeOffRequest>>(`${this.apiUrl}/requests/my`, { 
      headers: this.noCacheHeaders, 
      params 
    });
  }

  requestTimeOff(
    date: string,
    leaveType: string,
    startTime: string | null,
    endTime: string | null,
    durationHours: number,
    reason?: string,
    attachmentName?: string
  ): Observable<any> {
    return this.http.post(`${this.apiUrl}/requests`, {
      date,
      leave_type: leaveType,
      start_time: startTime,
      end_time: endTime,
      duration_hours: durationHours,
      reason: reason || null,
      attachment_name: attachmentName || null
    });
  }

  cancelTimeOffRequest(requestId: number): Observable<any> {
    return this.http.put(`${this.apiUrl}/requests/${requestId}/cancel`, {});
  }

  applyTimeOffInline(payload: {
    date: string;
    leave_type: string;
    start_time: string | null;
    end_time: string | null;
  }): Observable<TimeOffApplyResponse> {
    return this.http.post<TimeOffApplyResponse>(`${this.apiUrl}/apply`, {
      date: payload.date,
      leave_type: payload.leave_type,
      start_time: payload.start_time,
      end_time: payload.end_time
    });
  }

  getPendingTimeOffRequests(
    page: number = 1, 
    pageSize: number = 10, 
    search: string = '', 
    leaveType: string = ''
  ): Observable<PaginatedResponse<TimeOffRequest>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('pageSize', pageSize.toString())
      .set('search', search.trim())
      .set('leave_type', leaveType)
      .set('_ts', Date.now().toString());
    return this.http.get<PaginatedResponse<TimeOffRequest>>(`${this.apiUrl}/pending`, { 
      headers: this.noCacheHeaders, 
      params 
    });
  }

  getProcessedTimeOffRequests(
    page: number = 1, 
    pageSize: number = 10, 
    search: string = '', 
    leaveType: string = '', 
    status: string = ''
  ): Observable<PaginatedResponse<TimeOffRequest>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('pageSize', pageSize.toString())
      .set('search', search.trim())
      .set('leave_type', leaveType)
      .set('status', status)
      .set('_ts', Date.now().toString());
    return this.http.get<PaginatedResponse<TimeOffRequest>>(`${this.apiUrl}/history`, { 
      headers: this.noCacheHeaders, 
      params 
    });
  }

  approveTimeOffRequest(
    requestId: number, 
    action: string, 
    approvedHours?: number, 
    comments?: string
  ): Observable<any> {
    const decision = action.toLowerCase() === 'approve' ? 'approved' : 'rejected';
    return this.http.post(`${this.apiUrl}/requests/${requestId}/decision`, {
      decision,
      comment: comments || '',
      approvedHours: approvedHours ?? null
    });
  }

  triggerTimeOffUpdate(event: any): void {
    this.timeoffUpdateSubject.next(event);
  }
}
