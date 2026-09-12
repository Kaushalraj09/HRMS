import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import {
  MasterDataBootstrapResponse,
  Department,
  Designation,
  Shift,
  WorkLocation,
  LeaveType,
  Holiday
} from '../models/master-data.model';

// Helper to generate temporary entity codes
function generateCode(prefix: string, length = 6): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `${prefix}_${result}`;
}

// -- Data Adapters (Frontend <=> Backend model translation) --

function holidayToBackend(payload: Partial<Holiday>): Record<string, unknown> {
  const { date, ...rest } = payload as any;
  return {
    ...rest,
    holiday_date: date,
    description: rest.description ?? null,
    is_optional: rest.is_optional ?? false,
    is_active: rest.is_active ?? true,
  };
}

function holidayFromBackend(item: any): Holiday {
  return {
    id: item.id,
    name: item.name,
    date: item.holiday_date,
    is_active: item.is_active ?? true,
  };
}

function workLocationToBackend(payload: Partial<WorkLocation>, existingCode?: string): Record<string, unknown> {
  const { address, ...rest } = payload as any;
  return {
    ...rest,
    description: address ?? rest.description ?? null,
    code: existingCode ?? rest.code ?? generateCode('LOC'),
    location_type: rest.location_type ?? 'office',
    latitude: rest.latitude != null ? Number(rest.latitude) : null,
    longitude: rest.longitude != null ? Number(rest.longitude) : null,
    geofence_radius_meters: rest.geofence_radius_meters != null ? Number(rest.geofence_radius_meters) : 40.0,
    is_active: rest.is_active ?? true,
  };
}

function workLocationFromBackend(item: any): WorkLocation {
  return {
    id: item.id,
    name: item.name,
    code: item.code,
    address: item.description ?? item.address ?? undefined,
    description: item.description ?? undefined,
    location_type: item.location_type ?? 'office',
    latitude: item.latitude != null ? Number(item.latitude) : undefined,
    longitude: item.longitude != null ? Number(item.longitude) : undefined,
    geofence_radius_meters: item.geofence_radius_meters != null ? Number(item.geofence_radius_meters) : 40.0,
    is_active: item.is_active ?? true,
  };
}

function shiftToBackend(payload: Partial<Shift>, existingCode?: string): Record<string, unknown> {
  const { id, ...rest } = payload as any;
  return {
    ...rest,
    code: existingCode ?? rest.code ?? generateCode('SHIFT'),
    start_time: rest.start_time ?? null,
    end_time: rest.end_time ?? null,
    is_active: rest.is_active ?? true,
  };
}

function shiftFromBackend(item: any): Shift {
  return {
    ...item,
    start_time: item.start_time ?? '',
    end_time: item.end_time ?? '',
    is_active: item.is_active ?? true,
  };
}

function leaveTypeToBackend(payload: Partial<LeaveType>, existingCode?: string): Record<string, unknown> {
  const { max_days, ...rest } = payload as any;
  const daysValue = max_days != null ? Number(max_days) : null;
  return {
    name: rest.name,
    code: existingCode ?? rest.code ?? generateCode('LT'),
    unit_type: rest.unit_type ?? 'full_day',
    default_balance_hours: daysValue != null ? daysValue * 8 : 0, // 8 hours per day
    requires_approval: rest.requires_approval ?? true,
    applicable_employee_type: rest.applicable_employee_type ?? 'all',
    carry_forward: rest.carry_forward ?? false,
    max_consecutive_days: rest.max_consecutive_days != null ? Number(rest.max_consecutive_days) : null,
    counts_as_leave: rest.counts_as_leave ?? true,
    attendance_required: rest.attendance_required ?? false,
    remote_punch_allowed: rest.remote_punch_allowed ?? false,
    is_active: rest.is_active ?? true,
  };
}

function leaveTypeFromBackend(item: any): LeaveType {
  return {
    id: item.id,
    name: item.name,
    code: item.code,
    unit_type: item.unit_type ?? 'full_day',
    default_balance_hours: item.default_balance_hours != null ? Number(item.default_balance_hours) : undefined,
    max_days: item.default_balance_hours != null ? Math.round(Number(item.default_balance_hours) / 8) : undefined,
    applicable_employee_type: item.applicable_employee_type ?? 'all',
    carry_forward: item.carry_forward ?? false,
    max_consecutive_days: item.max_consecutive_days,
    counts_as_leave: item.counts_as_leave ?? true,
    attendance_required: item.attendance_required ?? false,
    remote_punch_allowed: item.remote_punch_allowed ?? false,
    is_active: item.is_active ?? true,
  };
}

@Injectable({
  providedIn: 'root'
})
export class MasterDataService {
  private readonly apiUrl = buildApiUrl('/master-data');
  private readonly noCacheHeaders = new HttpHeaders({
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
  });

  constructor(private readonly http: HttpClient) {}

  // Get all master entities for onboarding/bootstrapping
  getBootstrapData(): Observable<MasterDataBootstrapResponse> {
    return this.http.get<any>(`${this.apiUrl}/bootstrap`, {
      headers: this.noCacheHeaders
    }).pipe(
      map((res: any) => ({
        departments: (res.departments ?? []),
        designations: (res.designations ?? []),
        shifts: (res.shifts ?? []).map(shiftFromBackend),
        workLocations: (res.workLocations ?? res.work_locations ?? []).map(workLocationFromBackend),
        leaveTypes: (res.leaveTypes ?? res.leave_types ?? []).map(leaveTypeFromBackend),
        holidays: (res.holidays ?? []).map(holidayFromBackend),
      }))
    );
  }

  // --- Departments ---

  getDepartments(): Observable<Department[]> {
    return this.http.get<Department[]>(`${this.apiUrl}/departments`, { headers: this.noCacheHeaders });
  }

  createDepartment(payload: Partial<Department>): Observable<Department> {
    return this.http.post<Department>(`${this.apiUrl}/departments`, payload);
  }

  updateDepartment(id: number, payload: Partial<Department>): Observable<Department> {
    return this.http.put<Department>(`${this.apiUrl}/departments/${id}`, payload);
  }

  // --- Designations ---

  getDesignations(): Observable<Designation[]> {
    return this.http.get<Designation[]>(`${this.apiUrl}/designations`, { headers: this.noCacheHeaders });
  }

  createDesignation(payload: Partial<Designation>): Observable<Designation> {
    return this.http.post<Designation>(`${this.apiUrl}/designations`, payload);
  }

  updateDesignation(id: number, payload: Partial<Designation>): Observable<Designation> {
    return this.http.put<Designation>(`${this.apiUrl}/designations/${id}`, payload);
  }

  // --- Shifts ---

  getShifts(): Observable<Shift[]> {
    return this.http.get<any[]>(`${this.apiUrl}/shifts`, { headers: this.noCacheHeaders }).pipe(
      map(items => items.map(shiftFromBackend))
    );
  }

  createShift(payload: Partial<Shift>): Observable<Shift> {
    return this.http.post<any>(`${this.apiUrl}/shifts`, shiftToBackend(payload)).pipe(
      map(shiftFromBackend)
    );
  }

  updateShift(id: number, payload: Partial<Shift>): Observable<Shift> {
    const backendPayload = shiftToBackend(payload, (payload as any).code);
    return this.http.put<any>(`${this.apiUrl}/shifts/${id}`, backendPayload).pipe(
      map(shiftFromBackend)
    );
  }

  // --- Work Locations ---

  getWorkLocations(): Observable<WorkLocation[]> {
    return this.http.get<any[]>(`${this.apiUrl}/work-locations`, { headers: this.noCacheHeaders }).pipe(
      map(items => items.map(workLocationFromBackend))
    );
  }

  createWorkLocation(payload: Partial<WorkLocation>): Observable<WorkLocation> {
    return this.http.post<any>(`${this.apiUrl}/work-locations`, workLocationToBackend(payload)).pipe(
      map(workLocationFromBackend)
    );
  }

  updateWorkLocation(id: number, payload: Partial<WorkLocation>): Observable<WorkLocation> {
    const backendPayload = workLocationToBackend(payload, (payload as any).code);
    return this.http.put<any>(`${this.apiUrl}/work-locations/${id}`, backendPayload).pipe(
      map(workLocationFromBackend)
    );
  }

  // --- Leave Types ---

  getLeaveTypes(): Observable<LeaveType[]> {
    return this.http.get<any[]>(`${this.apiUrl}/leave-types`, { headers: this.noCacheHeaders }).pipe(
      map(items => items.map(leaveTypeFromBackend))
    );
  }

  createLeaveType(payload: Partial<LeaveType>): Observable<LeaveType> {
    return this.http.post<any>(`${this.apiUrl}/leave-types`, leaveTypeToBackend(payload)).pipe(
      map(leaveTypeFromBackend)
    );
  }

  updateLeaveType(id: number, payload: Partial<LeaveType>): Observable<LeaveType> {
    const backendPayload = leaveTypeToBackend(payload, (payload as any).code);
    return this.http.put<any>(`${this.apiUrl}/leave-types/${id}`, backendPayload).pipe(
      map(leaveTypeFromBackend)
    );
  }

  // --- Holidays ---

  getHolidays(): Observable<Holiday[]> {
    return this.http.get<any[]>(`${this.apiUrl}/holidays`, { headers: this.noCacheHeaders }).pipe(
      map(items => items.map(holidayFromBackend))
    );
  }

  createHoliday(payload: Partial<Holiday>): Observable<Holiday> {
    return this.http.post<any>(`${this.apiUrl}/holidays`, holidayToBackend(payload)).pipe(
      map(holidayFromBackend)
    );
  }

  updateHoliday(id: number, payload: Partial<Holiday>): Observable<Holiday> {
    return this.http.put<any>(`${this.apiUrl}/holidays/${id}`, holidayToBackend(payload)).pipe(
      map(holidayFromBackend)
    );
  }

  deleteDepartment(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/departments/${id}`);
  }

  deleteDesignation(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/designations/${id}`);
  }

  deleteShift(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/shifts/${id}`);
  }

  deleteWorkLocation(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/work-locations/${id}`);
  }

  deleteLeaveType(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/leave-types/${id}`);
  }

  deleteHoliday(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/holidays/${id}`);
  }
}

