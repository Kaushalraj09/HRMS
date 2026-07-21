import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import {
  RegularizationCreatePayload,
  RegularizationRequestItem,
  RegularizationDecisionPayload
} from '../models/regularization.model';
import { PaginatedResponse } from '../models/attendance.model';

@Injectable({
  providedIn: 'root'
})
export class RegularizationService {
  private readonly apiUrl = buildApiUrl('/regularizations');

  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
  });

  constructor(private readonly http: HttpClient) {}

  private noCacheParams(): HttpParams {
    return new HttpParams().set('_ts', Date.now().toString());
  }

  submitRegularization(payload: RegularizationCreatePayload): Observable<RegularizationRequestItem> {
    return this.http.post<RegularizationRequestItem>(
      this.apiUrl,
      payload,
      { headers: this.noCacheHeaders }
    );
  }

  getMyRequests(page: number = 1, pageSize: number = 10): Observable<PaginatedResponse<RegularizationRequestItem>> {
    const params = this.noCacheParams()
      .set('page', page.toString())
      .set('pageSize', pageSize.toString());
    return this.http.get<PaginatedResponse<RegularizationRequestItem>>(
      `${this.apiUrl}/my`,
      { headers: this.noCacheHeaders, params }
    );
  }

  getPendingRequests(page: number = 1, pageSize: number = 10, search: string = '', reasonType: string = ''): Observable<PaginatedResponse<RegularizationRequestItem>> {
    const params = this.noCacheParams()
      .set('page', page.toString())
      .set('pageSize', pageSize.toString())
      .set('search', search.trim())
      .set('reason_type', reasonType);
    return this.http.get<PaginatedResponse<RegularizationRequestItem>>(
      `${this.apiUrl}/pending`,
      { headers: this.noCacheHeaders, params }
    );
  }

  submitDecision(id: number, payload: RegularizationDecisionPayload): Observable<RegularizationRequestItem> {
    return this.http.put<RegularizationRequestItem>(
      `${this.apiUrl}/${id}/decision`,
      payload,
      { headers: this.noCacheHeaders }
    );
  }
}
