import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { buildApiUrl } from '../config/api.config';
import {
  SalaryComponent,
  SalaryStructure,
  SalaryCalculationRequest,
  SalaryCalculationPreview,
  EmployeeSalaryAssignment,
  EmployeeSalaryAssignmentCreate,
  EmployeeSalaryOverviewItem,
  SalaryRevision,
  SalaryRevisionCreate,
  PayrollPeriod,
  PayrollRunSummary,
  PayrollRunCreate,
  PayrollRecord,
  PayrollAdjustmentCreate,
  PayrollInput,
  PayrollInputCreate,
  PayrollException,
  Payslip,
  PayrollDashboardSummary,
  StatutoryConfiguration,
} from '../models/payroll.model';

@Injectable({
  providedIn: 'root',
})
export class PayrollService {
  constructor(private http: HttpClient) {}

  // ==========================================
  // Dashboard
  // ==========================================
  getDashboardSummary(): Observable<PayrollDashboardSummary> {
    return this.http.get<PayrollDashboardSummary>(buildApiUrl('/payroll/dashboard'));
  }

  // ==========================================
  // Salary Components
  // ==========================================
  getComponents(isActive?: boolean): Observable<SalaryComponent[]> {
    let params = new HttpParams();
    if (isActive !== undefined) {
      params = params.set('is_active', isActive);
    }
    return this.http.get<SalaryComponent[]>(buildApiUrl('/payroll/components'), { params });
  }

  createComponent(data: Partial<SalaryComponent>): Observable<SalaryComponent> {
    return this.http.post<SalaryComponent>(buildApiUrl('/payroll/components'), data);
  }

  updateComponent(id: number, data: Partial<SalaryComponent>): Observable<SalaryComponent> {
    return this.http.put<SalaryComponent>(buildApiUrl(`/payroll/components/${id}`), data);
  }

  deleteComponent(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(buildApiUrl(`/payroll/components/${id}`));
  }

  // ==========================================
  // Salary Structures
  // ==========================================
  getStructures(isActive?: boolean): Observable<SalaryStructure[]> {
    let params = new HttpParams();
    if (isActive !== undefined) {
      params = params.set('is_active', isActive);
    }
    return this.http.get<SalaryStructure[]>(buildApiUrl('/payroll/structures'), { params });
  }

  getStructure(id: number): Observable<SalaryStructure> {
    return this.http.get<SalaryStructure>(buildApiUrl(`/payroll/structures/${id}`));
  }

  createStructure(data: Partial<SalaryStructure>): Observable<SalaryStructure> {
    return this.http.post<SalaryStructure>(buildApiUrl('/payroll/structures'), data);
  }

  updateStructure(id: number, data: Partial<SalaryStructure>): Observable<SalaryStructure> {
    return this.http.put<SalaryStructure>(buildApiUrl(`/payroll/structures/${id}`), data);
  }

  // ==========================================
  // Salary Preview
  // ==========================================
  calculatePreview(data: SalaryCalculationRequest): Observable<SalaryCalculationPreview> {
    return this.http.post<SalaryCalculationPreview>(buildApiUrl('/payroll/calculate-preview'), data);
  }

  // ==========================================
  // Employee Salary Assignments
  // ==========================================
  getAllEmployeeSalaries(
    search?: string,
    department?: string,
    skip: number = 0,
    limit: number = 50
  ): Observable<{ total: number; items: EmployeeSalaryOverviewItem[] }> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (search) params = params.set('search', search);
    if (department) params = params.set('department', department);
    return this.http.get<{ total: number; items: EmployeeSalaryOverviewItem[] }>(
      buildApiUrl('/payroll/employee-salaries'),
      { params }
    );
  }

  getEmployeeSalary(employeeId: number): Observable<EmployeeSalaryAssignment> {
    return this.http.get<EmployeeSalaryAssignment>(buildApiUrl(`/payroll/employee-salaries/${employeeId}`));
  }

  assignEmployeeSalary(data: EmployeeSalaryAssignmentCreate): Observable<EmployeeSalaryAssignment> {
    return this.http.post<EmployeeSalaryAssignment>(buildApiUrl('/payroll/employee-salaries'), data);
  }

  getEmployeeSalaryHistory(employeeId: number): Observable<EmployeeSalaryAssignment[]> {
    return this.http.get<EmployeeSalaryAssignment[]>(
      buildApiUrl(`/payroll/employee-salaries/${employeeId}/history`)
    );
  }

  // ==========================================
  // Salary Revisions
  // ==========================================
  getRevisions(
    status?: string,
    employeeId?: number,
    skip: number = 0,
    limit: number = 50
  ): Observable<{ total: number; items: SalaryRevision[] }> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (status) params = params.set('status', status);
    if (employeeId) params = params.set('employee_id', employeeId);
    return this.http.get<{ total: number; items: SalaryRevision[] }>(buildApiUrl('/payroll/revisions'), { params });
  }

  createRevision(data: SalaryRevisionCreate): Observable<SalaryRevision> {
    return this.http.post<SalaryRevision>(buildApiUrl('/payroll/revisions'), data);
  }

  actionRevision(revisionId: number, approved: boolean, remarks?: string): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/revisions/${revisionId}/action`), { approved, remarks });
  }

  // ==========================================
  // Payroll Periods & Runs
  // ==========================================
  getPeriods(): Observable<PayrollPeriod[]> {
    return this.http.get<PayrollPeriod[]>(buildApiUrl('/payroll/periods'));
  }

  getRuns(year?: number, month?: number, status?: string): Observable<PayrollRunSummary[]> {
    let params = new HttpParams();
    if (year) params = params.set('year', year);
    if (month) params = params.set('month', month);
    if (status) params = params.set('status', status);
    return this.http.get<PayrollRunSummary[]>(buildApiUrl('/payroll/runs'), { params });
  }

  executeRun(data: PayrollRunCreate): Observable<PayrollRunSummary> {
    return this.http.post<PayrollRunSummary>(buildApiUrl('/payroll/runs'), data);
  }

  getRunDetail(runId: number): Observable<PayrollRunSummary> {
    return this.http.get<PayrollRunSummary>(buildApiUrl(`/payroll/runs/${runId}`));
  }

  submitRunForApproval(runId: number): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/runs/${runId}/submit-approval`), {});
  }

  approveOrRejectRun(runId: number, approved: boolean, remarks?: string): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/runs/${runId}/action`), { approved, remarks });
  }

  lockRun(runId: number): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/runs/${runId}/lock`), {});
  }

  markRunPaid(runId: number): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/runs/${runId}/mark-paid`), {});
  }

  // ==========================================
  // Payroll Records & Adjustments
  // ==========================================
  getPayrollRecords(
    runId: number,
    search?: string,
    department?: string,
    status?: string,
    skip: number = 0,
    limit: number = 50
  ): Observable<{ total: number; items: PayrollRecord[] }> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (search) params = params.set('search', search);
    if (department) params = params.set('department', department);
    if (status) params = params.set('status', status);
    return this.http.get<{ total: number; items: PayrollRecord[] }>(
      buildApiUrl(`/payroll/runs/${runId}/records`),
      { params }
    );
  }

  adjustPayrollRecord(recordId: number, data: PayrollAdjustmentCreate): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/records/${recordId}/adjust`), data);
  }

  // ==========================================
  // Payroll Inputs
  // ==========================================
  getPayrollInputs(periodId?: number, employeeId?: number): Observable<PayrollInput[]> {
    let params = new HttpParams();
    if (periodId) params = params.set('period_id', periodId);
    if (employeeId) params = params.set('employee_id', employeeId);
    return this.http.get<PayrollInput[]>(buildApiUrl('/payroll/inputs'), { params });
  }

  createPayrollInput(data: PayrollInputCreate): Observable<PayrollInput> {
    return this.http.post<PayrollInput>(buildApiUrl('/payroll/inputs'), data);
  }

  deletePayrollInput(inputId: number): Observable<any> {
    return this.http.delete(buildApiUrl(`/payroll/inputs/${inputId}`));
  }

  // ==========================================
  // Exceptions
  // ==========================================
  getExceptions(runId: number, severity?: string, isResolved?: boolean): Observable<PayrollException[]> {
    let params = new HttpParams();
    if (severity) params = params.set('severity', severity);
    if (isResolved !== undefined) params = params.set('is_resolved', isResolved);
    return this.http.get<PayrollException[]>(buildApiUrl(`/payroll/runs/${runId}/exceptions`), { params });
  }

  resolveException(exceptionId: number, resolutionNotes: string): Observable<any> {
    return this.http.post(buildApiUrl(`/payroll/exceptions/${exceptionId}/resolve`), {
      resolution_notes: resolutionNotes,
    });
  }

  // ==========================================
  // Payslips & Downloads
  // ==========================================
  getPayslips(
    employeeId?: number,
    month?: string,
    skip: number = 0,
    limit: number = 50
  ): Observable<{ total: number; items: Payslip[] }> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (employeeId) params = params.set('employee_id', employeeId);
    if (month) params = params.set('month', month);
    return this.http.get<{ total: number; items: Payslip[] }>(buildApiUrl('/payroll/payslips'), { params });
  }

  getPayslip(payslipId: number): Observable<Payslip> {
    return this.http.get<Payslip>(buildApiUrl(`/payroll/payslips/${payslipId}`));
  }

  downloadPayslipPdf(payslipId: number): Observable<Blob> {
    return this.http.get(buildApiUrl(`/payroll/payslips/${payslipId}/download`), {
      responseType: 'blob',
    });
  }

  exportPayrollCsv(runId: number): Observable<Blob> {
    return this.http.get(buildApiUrl(`/payroll/runs/${runId}/export-csv`), {
      responseType: 'blob',
    });
  }

  exportBankCsv(runId: number): Observable<Blob> {
    return this.http.get(buildApiUrl(`/payroll/runs/${runId}/export-bank-csv`), {
      responseType: 'blob',
    });
  }

  // ==========================================
  // Dedicated Employee Self-Service
  // ==========================================
  getMySalary(): Observable<EmployeeSalaryAssignment> {
    return this.http.get<EmployeeSalaryAssignment>(buildApiUrl('/payroll/my-salary'));
  }

  getMySalaryHistory(): Observable<EmployeeSalaryAssignment[]> {
    return this.http.get<EmployeeSalaryAssignment[]>(buildApiUrl('/payroll/my-salary-history'));
  }

  getMyPayslips(skip: number = 0, limit: number = 50): Observable<{ total: number; items: Payslip[] }> {
    const params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<{ total: number; items: Payslip[] }>(buildApiUrl('/payroll/my-payslips'), { params });
  }

  // ==========================================
  // Statutory Configurations
  // ==========================================
  getStatutoryConfigs(): Observable<StatutoryConfiguration[]> {
    return this.http.get<StatutoryConfiguration[]>(buildApiUrl('/payroll/statutory-configs'));
  }

  updateStatutoryConfig(id: number, data: Partial<StatutoryConfiguration>): Observable<StatutoryConfiguration> {
    return this.http.put<StatutoryConfiguration>(buildApiUrl(`/payroll/statutory-configs/${id}`), data);
  }
}
