import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import {
  RegularizationCreatePayload,
  RegularizationRequestItem,
  RegularizationDecisionPayload
} from '../models/regularization.model';

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

  getMyRequests(): Observable<RegularizationRequestItem[]> {
    return this.http.get<RegularizationRequestItem[]>(
      `${this.apiUrl}/my`,
      { headers: this.noCacheHeaders, params: this.noCacheParams() }
    );
  }

  getPendingRequests(): Observable<RegularizationRequestItem[]> {
    return this.http.get<RegularizationRequestItem[]>(
      `${this.apiUrl}/pending`,
      { headers: this.noCacheHeaders, params: this.noCacheParams() }
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
