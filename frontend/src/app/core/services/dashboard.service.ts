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

  getAdminDashboard(range: string = '30d'): Observable<AdminDashboardData> {
    return this.http.get<AdminDashboardData>(`${this.apiUrl}/admin?range=${encodeURIComponent(range)}`);
  }

  getHrDashboard(range: string = '30d'): Observable<HrDashboardData> {
    return this.http.get<HrDashboardData>(`${this.apiUrl}/hr?range=${encodeURIComponent(range)}`);
  }

  exportReport(cardType: string, range: string = '30d', format: string = 'pdf'): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/export?card_type=${encodeURIComponent(cardType)}&range=${encodeURIComponent(range)}&format=${encodeURIComponent(format)}`, {
      responseType: 'blob'
    });
  }
}

