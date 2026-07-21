import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { PaginatedResult } from '../models/employee.model';
import { CreateHrPayload, HrUser } from '../models/hr.model';

interface BackendHrUser {
  id: number;
  userId?: number;
  user_id?: number;
  hrCode?: string;
  hr_code?: string;
  fullName?: string;
  full_name?: string;
  email: string;
  phone: string;
  department: string;
  designation: string;
  status: 'Active' | 'Inactive';
  createdAt?: string;
  created_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class HrService {
  private readonly apiUrl = buildApiUrl('/hr-users');

  constructor(private readonly http: HttpClient) {}

  getHrUsers(page: number, limit: number, search: string, status: string): Observable<PaginatedResult<HrUser>> {
    const params = {
      page: String(page),
      limit: String(limit),
      search: search.trim(),
      status: status
    };

    return this.http.get<{ data: BackendHrUser[], total: number }>(this.apiUrl, { params }).pipe(
      map(res => ({
        data: res.data.map(row => this.mapHr(row)),
        total: res.total
      }))
    );
  }

  createHr(payload: CreateHrPayload): Observable<{ success: boolean; message: string; hr: HrUser }> {
    return this.http.post<BackendHrUser>(this.apiUrl, payload).pipe(
      map(row => {
        const hr = this.mapHr(row);
        return {
          success: true,
          message: `${hr.fullName} created successfully as HR`,
          hr
        };
      })
    );
  }

  private filterRows(rows: HrUser[], search: string, status: string): HrUser[] {
    return rows.filter(hr => {
      const searchValue = search.trim().toLowerCase();
      const matchesSearch = !searchValue
        || hr.fullName.toLowerCase().includes(searchValue)
        || hr.hrCode.toLowerCase().includes(searchValue)
        || hr.email.toLowerCase().includes(searchValue)
        || hr.department.toLowerCase().includes(searchValue);
      const matchesStatus = !status || hr.status === status;
      return matchesSearch && matchesStatus;
    });
  }

  private mapHr(row: BackendHrUser): HrUser {
    return {
      id: String(row.id),
      userId: String(row.userId ?? row.user_id ?? row.id),
      hrCode: row.hrCode ?? row.hr_code ?? '',
      fullName: row.fullName ?? row.full_name ?? '',
      email: row.email,
      phone: row.phone,
      department: row.department,
      designation: row.designation,
      status: row.status,
      login: row.status === 'Active' ? 'Enabled' : 'Disabled',
      createdAt: row.createdAt ?? row.created_at ?? ''
    };
  }
}
