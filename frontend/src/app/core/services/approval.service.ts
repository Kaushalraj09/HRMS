import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { ApprovalQueueResponse, ApprovalDecisionPayload, ApprovalTask } from '../models/approval.model';
import { PaginatedResponse } from '../models/attendance.model';

interface BackendApprovalQueueResponse {
  items: BackendApprovalItem[];
  counts: {
    timeoff: number;
    regularization: number;
    total: number;
  };
}

interface BackendApprovalItem {
  id: number;
  requestType: string;
  requestId: number;
  employeeId: number;
  employeeName: string;
  status: string;
  submittedAt: string;
  priority: string;
  reviewedBy?: number;
  reviewedAt?: string;
  decisionComment?: string;
  assignedRole?: string;
}

// Convert backend queue item to frontend task model
function backendItemToTask(item: BackendApprovalItem): ApprovalTask {
  return {
    id: item.id,
    request_type: item.requestType,
    request_id: item.requestId,
    employee_id: item.employeeId,
    employee_name: item.employeeName,
    employee_code: '', // default fallback as API does not provide this
    details: '',
    submitted_at: item.submittedAt,
    status: item.status,
    assigned_role: item.assignedRole,
    comment: item.decisionComment,
    reviewed_by: item.reviewedBy,
    reviewed_at: item.reviewedAt,
    duration_hours: undefined,
  };
}

// Separate pending approvals into categorised lists
function mapPendingResponse(res: BackendApprovalQueueResponse): ApprovalQueueResponse {
  const timeoffItems = res.items
    .filter(i => i.requestType === 'timeoff')
    .map(backendItemToTask);

  const regularizationItems = res.items
    .filter(i => i.requestType === 'regularization')
    .map(backendItemToTask);

  return {
    timeoff: timeoffItems,
    regularization: regularizationItems,
    total: res.counts?.total ?? res.items.length,
  };
}

@Injectable({
  providedIn: 'root'
})
export class ApprovalService {
  private readonly apiUrl = buildApiUrl('/approvals');
  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
  });

  constructor(private readonly http: HttpClient) {}

  getPendingApprovals(): Observable<ApprovalQueueResponse> {
    const params = new HttpParams().set('_ts', Date.now().toString());
    return this.http.get<BackendApprovalQueueResponse>(`${this.apiUrl}/pending`, {
      headers: this.noCacheHeaders,
      params
    }).pipe(
      map(mapPendingResponse)
    );
  }

  getApprovalHistory(
    page: number = 1,
    pageSize: number = 10,
    requestType?: string,
    employeeId?: string | number
  ): Observable<PaginatedResponse<ApprovalTask>> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('pageSize', pageSize.toString())
      .set('_ts', Date.now().toString());

    if (requestType) {
      params = params.set('requestType', requestType);
    }
    if (employeeId) {
      params = params.set('employeeId', employeeId.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/history`, {
      headers: this.noCacheHeaders,
      params
    }).pipe(
      map((res: any) => ({
        items: (res.items ?? []).map(backendItemToTask),
        totalItems: res.totalItems ?? 0,
        page: res.page ?? page,
        pageSize: res.pageSize ?? pageSize,
        totalPages: res.totalPages ?? 0,
      }))
    );
  }

  submitDecision(approvalTaskId: number, payload: ApprovalDecisionPayload): Observable<ApprovalTask> {
    const backendPayload: Record<string, unknown> = {
      decision: payload.decision,
    };
    if (payload.comment !== undefined) {
      backendPayload['comment'] = payload.comment;
    }
    if (payload.approved_hours !== undefined) {
      backendPayload['approvedHours'] = payload.approved_hours; // maps to API field alias
    }

    return this.http.post<BackendApprovalItem>(
      `${this.apiUrl}/${approvalTaskId}/decision`,
      backendPayload
    ).pipe(
      map(backendItemToTask)
    );
  }
}
