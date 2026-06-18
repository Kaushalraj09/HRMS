import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { buildApiUrl } from '../config/api.config';

export interface LoginActivity {
  id: number;
  user_id: number;
  employee_id?: number;
  login_time: string;
  browser?: string;
  device?: string;
  operating_system?: string;
  ip_address?: string;
  location?: string;
  status: string;
  created_at: string;
  employee_code?: string;
  employee_name?: string;
  user_display_name?: string;
}

@Injectable({
  providedIn: 'root'
})
export class LoginActivityService {
  private readonly apiUrl = buildApiUrl('/login-activity');

  constructor(private readonly http: HttpClient) {}

  getHistory(filterType?: string, startDate?: string, endDate?: string): Observable<LoginActivity[]> {
    let params = new HttpParams();
    if (filterType) {
      params = params.set('filter_type', filterType);
    }
    if (startDate) {
      params = params.set('start_date', startDate);
    }
    if (endDate) {
      params = params.set('end_date', endDate);
    }
    return this.http.get<LoginActivity[]>(this.apiUrl, { params });
  }

  getDetail(id: number): Observable<LoginActivity> {
    return this.http.get<LoginActivity>(`${this.apiUrl}/${id}`);
  }
}
