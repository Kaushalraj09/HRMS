export interface SalaryComponent {
  id: number;
  code: string;
  name: string;
  component_type: 'EARNING' | 'DEDUCTION' | 'STATUTORY_EMPLOYER';
  calculation_type: 'PERCENTAGE' | 'FIXED' | 'BALANCE' | 'ATTENDANCE' | 'HOURLY';
  calculation_basis?: 'CTC' | 'BASIC' | 'GROSS' | null;
  default_value: number;
  is_taxable: boolean;
  is_statutory: boolean;
  is_active: boolean;
  description?: string;
  sequence_order: number;
}

export interface StructureComponentItem {
  id?: number;
  component_id: number;
  component_code?: string;
  component_name?: string;
  component_type?: string;
  calculation_type: string;
  calculation_basis?: string | null;
  percentage_or_value: number;
  sequence_order: number;
  // UI helpers
  value?: number;
  is_taxable?: boolean;
}

export interface SalaryStructure {
  id: number;
  code: string;
  name: string;
  salary_basis: 'CTC' | 'GROSS';
  calculation_mode?: string; // UI alias for salary_basis
  description?: string;
  is_active: boolean;
  components: StructureComponentItem[];
}

export interface CalculatedComponentItem {
  component_id?: number;
  code: string;
  name: string;
  component_name?: string;
  component_code?: string;
  component_type: 'EARNING' | 'DEDUCTION' | 'STATUTORY_EMPLOYER' | string;
  calculation_type: string;
  percentage_or_value: number;
  monthly_amount: number;
  annual_amount: number;
  is_statutory: boolean;
}

export interface SalaryCalculationPreview {
  salary_basis: string;
  annual_ctc: number;
  monthly_ctc: number;
  gross_monthly: number;
  gross_annual: number;
  total_deductions_monthly: number;
  total_deductions_annual: number;
  net_monthly: number;
  net_annual: number;
  employer_contributions_monthly: number;
  employer_contributions_annual: number;
  total_employer_cost_monthly: number;
  earnings: CalculatedComponentItem[];
  deductions: CalculatedComponentItem[];
  employer_contributions: CalculatedComponentItem[];
  // UI aliases
  monthly_gross?: number;
  monthly_net?: number;
  monthly_deductions?: number;
  components?: CalculatedComponentItem[];
}

export interface SalaryCalculationRequest {
  employee_id?: number;
  structure_id: number;
  salary_basis: 'CTC' | 'GROSS';
  ctc_amount: number;
  salary_type?: 'Annual' | 'Monthly';
  calculation_mode?: string;
  base_amount?: number;
  custom_overrides?: { [key: string]: number };
}

export interface EmployeeSalaryAssignment {
  id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  department?: string;
  designation?: string;
  salary_structure_id: number;
  structure_name?: string;
  salary_basis: string;
  calculation_mode?: string;
  salary_type: string;
  annual_ctc: number;
  monthly_ctc: number;
  gross_monthly: number;
  net_monthly: number;
  total_deductions: number;
  employer_contributions: number;
  effective_from: string;
  effective_to?: string | null;
  is_active: boolean;
  breakdown?: SalaryCalculationPreview | null;
  created_at?: string;
  // UI aliases
  monthly_gross?: number;
  monthly_net?: number;
  components?: CalculatedComponentItem[];
}

export interface EmployeeSalaryAssignmentCreate {
  employee_id: number;
  salary_structure_id: number;
  structure_id?: number;
  salary_basis: 'CTC' | 'GROSS';
  calculation_mode?: string;
  salary_type: 'Annual' | 'Monthly';
  ctc_amount: number;
  base_amount?: number;
  effective_from: string;
  auto_calculate?: boolean;
  custom_overrides?: { [key: string]: number };
}

export interface EmployeeSalaryOverviewItem {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  department?: string;
  designation?: string;
  has_salary: boolean;
  has_salary_configured?: boolean;
  assignment_id?: number;
  structure_id?: number;
  structure_code?: string;
  structure_name?: string;
  salary_basis?: string;
  annual_ctc: number;
  monthly_ctc: number;
  gross_monthly: number;
  monthly_gross?: number;
  net_monthly: number;
  monthly_net?: number;
  effective_from?: string;
}

export interface SalaryRevision {
  id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  department?: string;
  designation?: string;
  new_salary_structure_id: number;
  structure_name?: string;
  old_annual_ctc: number;
  current_annual_ctc?: number;
  new_annual_ctc: number;
  proposed_annual_ctc?: number;
  old_monthly_gross: number;
  new_monthly_gross: number;
  increment_amount: number;
  increment_percentage: number;
  effective_from: string;
  effective_date?: string;
  reason: string;
  remarks?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | string;
  created_by: number;
  creator_name?: string;
  approved_by?: number;
  approver_name?: string;
  approved_at?: string;
  created_at?: string;
}

export interface SalaryRevisionCreate {
  employee_id: number;
  new_salary_structure_id: number;
  new_ctc_amount: number;
  salary_type?: 'Annual' | 'Monthly';
  effective_from: string;
  reason: string;
  remarks?: string;
  proposed_annual_ctc?: number;
  proposed_monthly_gross?: number;
  increment_percentage?: number;
}

export interface PayrollPeriod {
  id: number;
  name: string;
  year: number;
  month: number;
  start_date: string;
  end_date: string;
  pay_date: string;
  total_days: number;
  working_days: number;
  status: 'OPEN' | 'PROCESSING' | 'LOCKED' | 'PAID' | string;
}

export interface PayrollRunSummary {
  id: number;
  period_id: number;
  period_name: string;
  year?: number;
  month?: number;
  start_date?: string;
  end_date?: string;
  pay_date?: string;
  run_number: string;
  title: string;
  status: 'DRAFT' | 'PROCESSING' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'LOCKED' | 'PAID' | string;
  total_employees: number;
  processed_employees: number;
  warning_count: number;
  error_count: number;
  total_gross: number;
  total_deductions: number;
  total_net: number;
  total_employer_cost: number;
  calculated_at?: string;
  approved_at?: string;
  locked_at?: string;
  paid_at?: string;
}

export interface PayrollRunCreate {
  year: number;
  month: number;
  selected_employee_ids?: number[];
  pay_date?: string;
  remarks?: string;
}

export interface PayrollRecordItem {
  id: number;
  component_code: string;
  component_name: string;
  component_type: string;
  amount: number;
  calculation_detail?: string;
}

export interface PayrollRecord {
  id: number;
  payroll_run_id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  department?: string;
  designation?: string;
  status: string;
  
  // Days & Attendance
  total_payroll_days: number;
  month_days?: number;
  payable_days: number;
  paid_days?: number;
  present_days: number;
  absent_days: number;
  half_days: number;
  paid_leave_days: number;
  unpaid_leave_days: number;
  loss_of_pay_days?: number;
  holidays_count: number;
  weekly_offs_count: number;

  // Variable & Overtime
  overtime_hours: number;
  overtime_rate: number;
  overtime_amount: number;
  bonus_amount: number;
  incentive_amount: number;
  other_earnings_amount: number;
  lop_deduction_amount: number;
  other_deductions_amount: number;

  // Totals
  fixed_gross_salary: number;
  gross_earnings: number;
  total_deductions: number;
  net_salary: number;
  net_pay?: number;
  employer_pf: number;
  employer_esi: number;
  total_employer_contribution: number;
  total_cost_to_company: number;

  // Bank & Payment
  payment_status: string;
  payment_mode: string;
  bank_name?: string;
  account_number?: string;
  ifsc_code?: string;
  
  items: PayrollRecordItem[];
  calculation_snapshot?: any;
  created_at?: string;
}

export interface PayrollInput {
  id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  payroll_period_id: number;
  period_name?: string;
  input_type: string;
  title: string;
  amount: number;
  hours?: number;
  remarks?: string;
  status: string;
}

export interface PayrollInputCreate {
  employee_id: number;
  payroll_period_id: number;
  input_type: string;
  title: string;
  amount: number;
  hours?: number;
  remarks?: string;
}

export interface PayrollException {
  id: number;
  payroll_run_id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  department?: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO' | string;
  error_code: string;
  exception_type?: string;
  message: string;
  is_resolved: boolean;
  resolution_notes?: string;
  created_at?: string;
}

export interface PayrollAdjustmentCreate {
  payroll_record_id: number;
  component_code: string;
  new_amount: number;
  reason: string;
  adjustment_type?: string;
  amount?: number;
}

export interface PayrollAdjustmentResponse {
  id: number;
  payroll_record_id: number;
  component_code: string;
  old_amount: float;
  new_amount: float;
  difference: float;
  reason: string;
  status: string;
  created_at?: string;
}

type float = number;

export interface Payslip {
  id: number;
  payroll_record_id: number;
  employee_id: number;
  employee_code: string;
  employee_name: string;
  department?: string;
  designation?: string;
  doj?: string;
  payslip_number: string;
  payroll_month: string;
  month?: string;
  year?: number;
  
  total_payroll_days: number;
  working_days?: number;
  payable_days: number;
  paid_days?: number;
  unpaid_leave_days: number;
  
  gross_earnings: number;
  total_deductions: number;
  net_salary: number;
  net_pay?: number;
  
  earnings: { code: string; name: string; amount: number; detail?: string }[];
  deductions: { code: string; name: string; amount: number; detail?: string }[];
  employer_contributions: { code: string; name: string; amount: number; detail?: string }[];
  
  bank_name?: string;
  account_number?: string;
  ifsc_code?: string;
  
  is_published: boolean;
  generated_at?: string;
}

export interface PayrollDashboardSummary {
  total_employees: number;
  assigned_salary_count: number;
  configured_salaries?: number;
  missing_salary_count: number;
  missing_salaries?: number;
  current_run?: PayrollRunSummary | null;
  previous_month_net: number;
  current_month_net: number;
  last_net_payout?: number;
  net_variance_pct: number;
  monthly_variance?: number;
  department_costs: { department: string; monthly_cost: number; employee_count?: number; total_cost?: number }[];
  department_cost_breakdown?: { department: string; total_cost: number; employee_count: number }[];
  salary_range_distribution: { range: string; count: number }[];
  statutory_summary: { [key: string]: number };
}

export interface StatutoryConfiguration {
  id: number;
  code: string;
  name: string;
  rule_name?: string;
  rule_type?: string;
  value?: number;
  employee_rate_pct: number;
  employer_rate_pct: number;
  wage_ceiling?: number | null;
  min_wage_threshold: number;
  calculation_basis: string;
  is_enabled: boolean;
  effective_from?: string;
  notes?: string;
  description?: string;
}
