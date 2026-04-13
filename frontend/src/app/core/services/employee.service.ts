import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { Employee, PaginatedResult, EmployeePayload } from '../models/employee.model';

@Injectable({ providedIn: 'root' })
export class EmployeeService {
  private mockEmployees: Employee[] = [
    { id: '1', employeeCode: 'EMP-001', name: 'Kaushal Raj', department: 'Engineering', designation: 'Full Stack Developer', employeeType: 'Full-Time', status: 'Active', login: 'Enabled' },
    { id: '2', employeeCode: 'EMP-002', name: 'John Doe', department: 'HR', designation: 'HR Manager', employeeType: 'Full-Time', status: 'Active', login: 'Enabled' },
    { id: '3', employeeCode: 'EMP-003', name: 'Jane Smith', department: 'Finance', designation: 'Accountant', employeeType: 'Part-Time', status: 'Inactive', login: 'Disabled' },
    { id: '4', employeeCode: 'EMP-004', name: 'Emily Davis', department: 'Marketing', designation: 'SEO Specialist', employeeType: 'Full-Time', status: 'Active', login: 'Enabled' },
    { id: '5', employeeCode: 'EMP-005', name: 'Michael Brown', department: 'Engineering', designation: 'QA Engineer', employeeType: 'Contract', status: 'Active', login: 'Enabled' },
    { id: '6', employeeCode: 'EMP-006', name: 'William Jones', department: 'Sales', designation: 'Sales Executive', employeeType: 'Full-Time', status: 'Active', login: 'Enabled' },
    { id: '7', employeeCode: 'EMP-007', name: 'Olivia Miller', department: 'Engineering', designation: 'DevOps Engineer', employeeType: 'Full-Time', status: 'Inactive', login: 'Disabled' },
    { id: '8', employeeCode: 'EMP-008', name: 'James Wilson', department: 'Support', designation: 'Support Tier 1', employeeType: 'Part-Time', status: 'Active', login: 'Enabled' },
    { id: '9', employeeCode: 'EMP-009', name: 'Benjamin Taylor', department: 'Marketing', designation: 'Content Writer', employeeType: 'Intern', status: 'Active', login: 'Enabled' },
    { id: '10', employeeCode: 'EMP-010', name: 'Sophia Anderson', department: 'Engineering', designation: 'Frontend Developer', employeeType: 'Full-Time', status: 'Active', login: 'Enabled' },
    { id: '11', employeeCode: 'EMP-011', name: 'Jacob Thomas', department: 'HR', designation: 'Recruiter', employeeType: 'Contract', status: 'Inactive', login: 'Disabled' },
    { id: '12', employeeCode: 'EMP-012', name: 'Isabella Jackson', department: 'Finance', designation: 'Financial Analyst', employeeType: 'Full-Time', status: 'Active', login: 'Enabled' },
  ];

  getEmployees(page: number, limit: number, search: string, department: string, type: string, status: string): Observable<PaginatedResult<Employee>> {
    let filtered = [...this.mockEmployees];

    if (search) {
      const s = search.toLowerCase();
      filtered = filtered.filter(e => e.name.toLowerCase().includes(s) || e.employeeCode.toLowerCase().includes(s) || e.department.toLowerCase().includes(s));
    }
    if (department) {
      filtered = filtered.filter(e => e.department === department);
    }
    if (type) {
      filtered = filtered.filter(e => e.employeeType === type);
    }
    if (status) {
      filtered = filtered.filter(e => e.status === status);
    }

    const startIndex = (page - 1) * limit;
    const paginatedItems = filtered.slice(startIndex, startIndex + limit);

    return of({
      data: paginatedItems,
      total: filtered.length
    }).pipe(delay(800));
  }

  createEmployee(payload: EmployeePayload): Observable<{success: boolean, message: string}> {
    console.log('Sending Add Employee Request: ', payload);
    return of({ success: true, message: 'Employee created successfully' }).pipe(delay(1000));
  }
}
