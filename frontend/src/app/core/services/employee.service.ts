import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { Employee, EmployeeDetailView, PaginatedResult, EmployeePayload } from '../models/employee.model';

import { Phase1StoreService } from './phase1-store.service';

@Injectable({ providedIn: 'root' })
export class EmployeeService {
  constructor(private readonly store: Phase1StoreService) {}

  getEmployees(page: number, limit: number, search: string, department: string, type: string, status: string): Observable<PaginatedResult<Employee>> {
    return of(this.store.listEmployees({ page, limit, search, department, type, status })).pipe(delay(300));
  }

  getEmployeeById(employeeId: string): Observable<EmployeeDetailView | null> {
    return of(this.store.getEmployeeById(employeeId)).pipe(delay(250));
  }

  createEmployee(payload: EmployeePayload): Observable<{ success: boolean; message: string; employee: Employee }> {
    return of(this.store.createEmployee(payload)).pipe(delay(500));
  }

  updateEmployee(employeeId: string, payload: EmployeePayload): Observable<{ success: boolean; message: string }> {
    return of(this.store.updateEmployee(employeeId, payload)).pipe(delay(400));
  }
}
