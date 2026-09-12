from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ==========================================
# Salary Components
# ==========================================
class SalaryComponentBase(BaseModel):
    code: str
    name: str
    component_type: str  # EARNING, DEDUCTION, STATUTORY_EMPLOYER
    calculation_type: str = "PERCENTAGE"  # PERCENTAGE, FIXED, BALANCE, ATTENDANCE, HOURLY
    calculation_basis: Optional[str] = None  # CTC, BASIC, GROSS
    default_value: float = 0.0
    is_taxable: bool = True
    is_statutory: bool = False
    is_active: bool = True
    description: Optional[str] = None
    sequence_order: int = 1


class SalaryComponentCreate(SalaryComponentBase):
    pass


class SalaryComponentUpdate(BaseModel):
    name: Optional[str] = None
    component_type: Optional[str] = None
    calculation_type: Optional[str] = None
    calculation_basis: Optional[str] = None
    default_value: Optional[float] = None
    is_taxable: Optional[bool] = None
    is_statutory: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    sequence_order: Optional[int] = None


class SalaryComponentResponse(SalaryComponentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Salary Structures
# ==========================================
class StructureComponentItem(BaseModel):
    component_id: int
    calculation_type: str
    calculation_basis: Optional[str] = None
    percentage_or_value: float = 0.0
    sequence_order: int = 1


class SalaryStructureBase(BaseModel):
    code: str
    name: str
    salary_basis: str = "CTC"  # CTC or GROSS
    description: Optional[str] = None
    is_active: bool = True


class SalaryStructureCreate(SalaryStructureBase):
    components: List[StructureComponentItem] = []


class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = None
    salary_basis: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    components: Optional[List[StructureComponentItem]] = None


class SalaryStructureComponentResponse(BaseModel):
    id: int
    component_id: int
    component_code: str
    component_name: str
    component_type: str
    calculation_type: str
    calculation_basis: Optional[str] = None
    percentage_or_value: float
    sequence_order: int
    model_config = ConfigDict(from_attributes=True)


class SalaryStructureResponse(SalaryStructureBase):
    id: int
    components: List[SalaryStructureComponentResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Dynamic Salary Preview & Calculation
# ==========================================
class SalaryCalculationRequest(BaseModel):
    employee_id: Optional[int] = None
    structure_id: int
    salary_basis: str = "CTC"  # CTC or GROSS
    ctc_amount: float
    salary_type: str = "Annual"  # Annual or Monthly
    custom_overrides: Optional[Dict[str, float]] = None  # e.g. {"BASIC": 50, "HRA": 40}


class CalculatedComponentItem(BaseModel):
    component_id: Optional[int] = None
    code: str
    name: str
    component_type: str  # EARNING, DEDUCTION, STATUTORY_EMPLOYER
    calculation_type: str
    percentage_or_value: float
    monthly_amount: float
    annual_amount: float
    is_statutory: bool = False


class SalaryCalculationPreview(BaseModel):
    salary_basis: str
    annual_ctc: float
    monthly_ctc: float
    gross_monthly: float
    gross_annual: float
    total_deductions_monthly: float
    total_deductions_annual: float
    net_monthly: float
    net_annual: float
    employer_contributions_monthly: float
    employer_contributions_annual: float
    total_employer_cost_monthly: float
    earnings: List[CalculatedComponentItem] = []
    deductions: List[CalculatedComponentItem] = []
    employer_contributions: List[CalculatedComponentItem] = []


# ==========================================
# Employee Salary Assignments
# ==========================================
class EmployeeSalaryAssignmentCreate(BaseModel):
    employee_id: int
    salary_structure_id: int
    salary_basis: str = "CTC"
    salary_type: str = "Annual"
    ctc_amount: float
    effective_from: date
    auto_calculate: bool = True
    custom_overrides: Optional[Dict[str, float]] = None


class EmployeeSalaryAssignmentResponse(BaseModel):
    id: int
    employee_id: int
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    salary_structure_id: int
    structure_name: Optional[str] = None
    salary_basis: str
    salary_type: str
    annual_ctc: float
    monthly_ctc: float
    gross_monthly: float
    net_monthly: float
    total_deductions: float
    employer_contributions: float
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool
    breakdown: Optional[SalaryCalculationPreview] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Salary Revisions
# ==========================================
class SalaryRevisionCreate(BaseModel):
    employee_id: int
    new_salary_structure_id: int
    new_ctc_amount: float
    salary_type: str = "Annual"
    effective_from: date
    reason: str = "Performance Increment"
    remarks: Optional[str] = None


class SalaryRevisionAction(BaseModel):
    approved: bool
    remarks: Optional[str] = None


class SalaryRevisionResponse(BaseModel):
    id: int
    employee_id: int
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    new_salary_structure_id: int
    structure_name: Optional[str] = None
    old_annual_ctc: float
    new_annual_ctc: float
    old_monthly_gross: float
    new_monthly_gross: float
    increment_amount: float
    increment_percentage: float
    effective_from: date
    reason: str
    remarks: Optional[str] = None
    status: str
    created_by: int
    creator_name: Optional[str] = None
    approved_by: Optional[int] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Payroll Period & Runs
# ==========================================
class PayrollPeriodResponse(BaseModel):
    id: int
    name: str
    year: int
    month: int
    start_date: date
    end_date: date
    pay_date: date
    total_days: int
    working_days: int
    status: str
    model_config = ConfigDict(from_attributes=True)


class PayrollRunCreate(BaseModel):
    year: int
    month: int
    selected_employee_ids: Optional[List[int]] = None  # None = All active employees
    pay_date: Optional[date] = None


class PayrollRunSummaryResponse(BaseModel):
    id: int
    period_id: int
    period_name: str
    run_number: str
    title: str
    status: str
    total_employees: int
    processed_employees: int
    warning_count: int
    error_count: int
    total_gross: float
    total_deductions: float
    total_net: float
    total_employer_cost: float
    calculated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Payroll Record & Items
# ==========================================
class PayrollRecordItemResponse(BaseModel):
    id: int
    component_code: str
    component_name: str
    component_type: str
    amount: float
    calculation_detail: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PayrollRecordResponse(BaseModel):
    id: int
    payroll_run_id: int
    employee_id: int
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    status: str
    
    # Days & Attendance
    total_payroll_days: float
    payable_days: float
    present_days: float
    absent_days: float
    half_days: float
    paid_leave_days: float
    unpaid_leave_days: float
    holidays_count: float
    weekly_offs_count: float

    # Variable & Overtime
    overtime_hours: float
    overtime_rate: float
    overtime_amount: float
    bonus_amount: float
    incentive_amount: float
    other_earnings_amount: float
    lop_deduction_amount: float
    other_deductions_amount: float

    # Totals
    fixed_gross_salary: float
    gross_earnings: float
    total_deductions: float
    net_salary: float
    employer_pf: float
    employer_esi: float
    total_employer_contribution: float
    total_cost_to_company: float

    # Bank & Payment
    payment_status: str
    payment_mode: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    
    items: List[PayrollRecordItemResponse] = []
    calculation_snapshot: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Payroll Inputs (Bonuses, Overrides)
# ==========================================
class PayrollInputCreate(BaseModel):
    employee_id: int
    payroll_period_id: int
    input_type: str  # BONUS, INCENTIVE, OVERTIME_OVERRIDE, OTHER_DEDUCTION, LOAN_ADVANCE, LOP_OVERRIDE
    title: str
    amount: float = 0.0
    hours: Optional[float] = None
    remarks: Optional[str] = None


class PayrollInputResponse(BaseModel):
    id: int
    employee_id: int
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    payroll_period_id: int
    period_name: Optional[str] = None
    input_type: str
    title: str
    amount: float
    hours: Optional[float] = None
    remarks: Optional[str] = None
    status: str
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Payroll Exceptions & Adjustments
# ==========================================
class PayrollExceptionResponse(BaseModel):
    id: int
    payroll_run_id: int
    employee_id: int
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    severity: str  # CRITICAL, WARNING, INFO
    error_code: str
    message: str
    is_resolved: bool
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ResolveExceptionRequest(BaseModel):
    resolution_notes: str


class PayrollAdjustmentCreate(BaseModel):
    payroll_record_id: int
    component_code: str
    new_amount: float
    reason: str


class PayrollAdjustmentResponse(BaseModel):
    id: int
    payroll_record_id: int
    component_code: str
    old_amount: float
    new_amount: float
    difference: float
    reason: str
    status: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Payslips
# ==========================================
class PayslipResponse(BaseModel):
    id: int
    payroll_record_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    doj: Optional[date] = None
    payslip_number: str
    payroll_month: str
    
    total_payroll_days: float
    payable_days: float
    unpaid_leave_days: float
    
    gross_earnings: float
    total_deductions: float
    net_salary: float
    
    earnings: List[Dict[str, Any]] = []
    deductions: List[Dict[str, Any]] = []
    employer_contributions: List[Dict[str, Any]] = []
    
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    
    is_published: bool
    generated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Dashboard Analytics & Reports
# ==========================================
class PayrollDashboardSummary(BaseModel):
    total_employees: int = 0
    assigned_salary_count: int = 0
    missing_salary_count: int = 0
    current_run: Optional[PayrollRunSummaryResponse] = None
    previous_month_net: float = 0.0
    current_month_net: float = 0.0
    net_variance_pct: float = 0.0
    department_costs: List[Dict[str, Any]] = []
    salary_range_distribution: List[Dict[str, Any]] = []
    statutory_summary: Dict[str, float] = {}


class StatutoryConfigurationResponse(BaseModel):
    id: int
    code: str
    name: str
    employee_rate_pct: float
    employer_rate_pct: float
    wage_ceiling: Optional[float] = None
    min_wage_threshold: float
    calculation_basis: str
    is_enabled: bool
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class StatutoryConfigurationUpdate(BaseModel):
    employee_rate_pct: Optional[float] = None
    employer_rate_pct: Optional[float] = None
    wage_ceiling: Optional[float] = None
    min_wage_threshold: Optional[float] = None
    calculation_basis: Optional[str] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
