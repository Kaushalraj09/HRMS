import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { AdminDashboardData, HrDashboardData } from '../models/dashboard.model';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly apiUrl = buildApiUrl('/dashboard');

  constructor(private readonly http: HttpClient) {}

  getAdminDashboard(): Observable<AdminDashboardData> {
    return this.http.get<AdminDashboardData>(`${this.apiUrl}/admin`);
  }

  getHrDashboard(): Observable<HrDashboardData> {
    return this.http.get<HrDashboardData>(`${this.apiUrl}/hr`);
  }
}
