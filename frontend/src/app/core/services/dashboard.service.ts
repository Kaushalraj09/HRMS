import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { AdminDashboardData, HrDashboardData } from '../models/dashboard.model';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/dashboard';

  constructor(private readonly http: HttpClient) {}

  getAdminDashboard(): Observable<AdminDashboardData> {
    return this.http.get<AdminDashboardData>(`${this.apiUrl}/admin`);
  }

  getHrDashboard(): Observable<HrDashboardData> {
    return this.http.get<HrDashboardData>(`${this.apiUrl}/hr`);
  }
}
