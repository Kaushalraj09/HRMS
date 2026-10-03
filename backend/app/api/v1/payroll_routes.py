from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.enums import UserRole
from app.schemas.payroll import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
    SalaryComponentResponse,
    SalaryStructureCreate,
    SalaryStructureUpdate,
    SalaryStructureResponse,
    SalaryCalculationRequest,
    SalaryCalculationPreview,
    EmployeeSalaryAssignmentCreate,
    EmployeeSalaryAssignmentResponse,
    SalaryRevisionCreate,
    SalaryRevisionAction,
    SalaryRevisionResponse,
    PayrollPeriodResponse,
    PayrollRunCreate,
    PayrollRunSummaryResponse,
    PayrollRecordResponse,
    PayrollAdjustmentCreate,
    PayrollAdjustmentResponse,
    PayrollInputCreate,
    PayrollInputResponse,
    PayrollExceptionResponse,
    ResolveExceptionRequest,
    PayslipResponse,
    PayrollDashboardSummary,
    StatutoryConfigurationResponse,
    StatutoryConfigurationUpdate,
)
from app.services.payroll_service import PayrollService

router = APIRouter(prefix="/payroll", tags=["payroll-management"])


def require_hr_or_admin(user: User):
    if not user.role or user.role.name.lower() not in [UserRole.ADMIN, UserRole.HR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Requires HR or Admin role.",
        )


def get_current_employee_id(user: User) -> int:
    emp_id = user.linked_employee_id
    if not emp_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No employee profile linked to current user account.",
        )
    return emp_id


# =============================================================================
# Dashboard Summary
# =============================================================================
@router.get("/dashboard", response_model=PayrollDashboardSummary)
def get_payroll_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_dashboard_summary(db)


# =============================================================================
# Salary Components
# =============================================================================
@router.get("/components", response_model=List[SalaryComponentResponse])
def get_components(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_components(db, is_active=is_active)


@router.post("/components", response_model=SalaryComponentResponse)
def create_component(
    data: SalaryComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.create_component(db, data, user_id=current_user.id)


@router.put("/components/{component_id}", response_model=SalaryComponentResponse)
def update_component(
    component_id: int,
    data: SalaryComponentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.update_component(db, component_id, data, user_id=current_user.id)


@router.delete("/components/{component_id}")
def delete_component(
    component_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.delete_component(db, component_id, user_id=current_user.id)


# =============================================================================
# Salary Structures
# =============================================================================
@router.get("/structures", response_model=List[SalaryStructureResponse])
def get_structures(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_structures(db, is_active=is_active)


@router.get("/structures/{structure_id}", response_model=SalaryStructureResponse)
def get_structure(
    structure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_structure(db, structure_id)


@router.post("/structures", response_model=SalaryStructureResponse)
def create_structure(
    data: SalaryStructureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.create_structure(db, data, user_id=current_user.id)


@router.put("/structures/{structure_id}", response_model=SalaryStructureResponse)
def update_structure(
    structure_id: int,
    data: SalaryStructureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.update_structure(db, structure_id, data, user_id=current_user.id)


@router.delete("/structures/{structure_id}")
def delete_structure(
    structure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.delete_structure(db, structure_id, user_id=current_user.id)


# =============================================================================
# Salary Preview & Calculation Simulation
# =============================================================================
@router.post("/calculate-preview", response_model=SalaryCalculationPreview)
def preview_salary_calculation(
    req: SalaryCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.preview_salary(db, req)


# =============================================================================
# Employee Salary Assignments
# =============================================================================
@router.get("/employee-salaries")
def get_all_employee_salaries(
    search: Optional[str] = None,
    department: Optional[str] = Query(None, description="Department name filter"),
    department_id: Optional[str] = Query(None, description="Legacy department filter fallback"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    dept_filter = department or department_id
    return PayrollService.get_all_employee_salaries(db, search, dept_filter, skip, limit)


@router.get("/employee-salaries/{employee_id}")
def get_employee_salary(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    res = PayrollService.get_employee_salary(db, employee_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active salary assignment found for this employee.")
    return res


@router.post("/employee-salaries")
def assign_employee_salary(
    data: EmployeeSalaryAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    assignment = PayrollService.assign_employee_salary(db, data, user_id=current_user.id)
    return PayrollService.get_employee_salary(db, assignment.employee_id)


@router.get("/employee-salaries/{employee_id}/history")
def get_employee_salary_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_salary_history(db, employee_id)


# =============================================================================
# Salary Revisions
# =============================================================================
@router.get("/revisions")
def get_salary_revisions(
    status: Optional[str] = None,
    employee_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_revisions(db, status_filter=status, employee_id=employee_id, skip=skip, limit=limit)


@router.post("/revisions")
def create_salary_revision(
    data: SalaryRevisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.create_revision(db, data, user_id=current_user.id)


@router.post("/revisions/{revision_id}/action")
def action_salary_revision(
    revision_id: int,
    action: SalaryRevisionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.action_revision(db, revision_id, action, user_id=current_user.id)


# =============================================================================
# Payroll Periods & Runs
# =============================================================================
@router.get("/periods", response_model=List[PayrollPeriodResponse])
def get_payroll_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_periods(db)


@router.get("/runs", response_model=List[PayrollRunSummaryResponse])
def get_payroll_runs(
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_runs(db, year, month, status)


@router.post("/runs")
def execute_payroll_run(
    data: PayrollRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    run = PayrollService.execute_payroll_run(db, data, user_id=current_user.id)
    return PayrollService.get_run_detail(db, run.id)


@router.get("/runs/{run_id}")
def get_payroll_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_run_detail(db, run_id)


@router.post("/runs/{run_id}/submit-approval")
def submit_run_for_approval(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.submit_run_for_approval(db, run_id, user_id=current_user.id)


@router.post("/runs/{run_id}/action")
def approve_or_reject_run(
    run_id: int,
    action: SalaryRevisionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.approve_or_reject_run(db, run_id, action.approved, user_id=current_user.id, remarks=action.remarks)


@router.post("/runs/{run_id}/lock")
def lock_payroll_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.lock_payroll_run(db, run_id, user_id=current_user.id)


@router.post("/runs/{run_id}/mark-paid")
def mark_payroll_run_paid(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.mark_run_paid(db, run_id, user_id=current_user.id)


@router.delete("/runs/{run_id}")
def delete_payroll_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.delete_payroll_run(db, run_id, user_id=current_user.id)


# =============================================================================
# Payroll Records & Adjustments
# =============================================================================
@router.get("/runs/{run_id}/records")
def get_payroll_records(
    run_id: int,
    search: Optional[str] = None,
    department: Optional[str] = Query(None, description="Department name filter"),
    department_id: Optional[str] = Query(None, description="Legacy department filter fallback"),
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    dept_filter = department or department_id
    return PayrollService.get_payroll_records(db, run_id, search, dept_filter, status, skip, limit)


@router.post("/records/{record_id}/adjust")
def adjust_payroll_record(
    record_id: int,
    data: PayrollAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.adjust_payroll_record(db, record_id, data, user_id=current_user.id)


# =============================================================================
# Payroll Inputs
# =============================================================================
@router.get("/inputs", response_model=List[PayrollInputResponse])
def get_payroll_inputs(
    period_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_payroll_inputs(db, period_id, employee_id)


@router.post("/inputs", response_model=PayrollInputResponse)
def create_payroll_input(
    data: PayrollInputCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.create_payroll_input(db, data, user_id=current_user.id)


@router.delete("/inputs/{input_id}")
def delete_payroll_input(
    input_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.delete_payroll_input(db, input_id, user_id=current_user.id)


# =============================================================================
# Exceptions
# =============================================================================
@router.get("/runs/{run_id}/exceptions", response_model=List[PayrollExceptionResponse])
def get_run_exceptions(
    run_id: int,
    severity: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_exceptions(db, run_id, severity, is_resolved)


@router.post("/exceptions/{exception_id}/resolve")
def resolve_run_exception(
    exception_id: int,
    data: ResolveExceptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.resolve_exception(db, exception_id, data.resolution_notes, user_id=current_user.id)


@router.post("/runs/{run_id}/exceptions/resolve-all")
def resolve_all_run_exceptions(
    run_id: int,
    data: ResolveExceptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.resolve_all_exceptions(db, run_id, data.resolution_notes, user_id=current_user.id)


# =============================================================================
# Reports & Exports (PDF Format)
# =============================================================================
@router.get("/runs/{run_id}/export-pdf")
@router.get("/runs/{run_id}/export-csv")
def export_payroll_pdf(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.export_payroll_pdf(db, run_id)


@router.get("/runs/{run_id}/export-bank-pdf")
@router.get("/runs/{run_id}/export-bank-csv")
def export_bank_transfer_pdf(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.export_bank_transfer_pdf(db, run_id)


# =============================================================================
# Payslips & Employee Self-Service
# =============================================================================
@router.get("/payslips")
def get_payslips(
    employee_id: Optional[int] = None,
    month: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_role = current_user.role.name.lower() if current_user.role else ""
    if user_role not in [UserRole.ADMIN, UserRole.HR]:
        # Non-HR employees can only view their own published payslips
        emp_id = get_current_employee_id(current_user)
        return PayrollService.get_payslips(db, employee_id=emp_id, month=month, is_published=True, skip=skip, limit=limit)

    return PayrollService.get_payslips(db, employee_id=employee_id, month=month, skip=skip, limit=limit)


@router.get("/payslips/{payslip_id}")
def get_payslip(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slip = PayrollService.get_payslip_detail(db, payslip_id)
    user_role = current_user.role.name.lower() if current_user.role else ""
    if user_role not in [UserRole.ADMIN, UserRole.HR]:
        emp_id = get_current_employee_id(current_user)
        slip_emp_id = slip.get("employee_id") if isinstance(slip, dict) else slip.employee_id
        if slip_emp_id != emp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this payslip.")
    return slip


@router.get("/payslips/{payslip_id}/download")
def download_payslip_pdf(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slip = PayrollService.get_payslip_detail(db, payslip_id)
    user_role = current_user.role.name.lower() if current_user.role else ""
    if user_role not in [UserRole.ADMIN, UserRole.HR]:
        emp_id = get_current_employee_id(current_user)
        slip_emp_id = slip.get("employee_id") if isinstance(slip, dict) else slip.employee_id
        if slip_emp_id != emp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this payslip.")
    return PayrollService.generate_payslip_pdf(db, payslip_id)


# =============================================================================
# Dedicated Employee Self-Service Endpoints
# =============================================================================
@router.get("/my-salary")
def get_my_salary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_id = get_current_employee_id(current_user)
    res = PayrollService.get_employee_salary(db, emp_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active salary details configured.")
    return res


@router.get("/my-salary-history")
def get_my_salary_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_id = get_current_employee_id(current_user)
    return PayrollService.get_salary_history(db, emp_id)


@router.get("/my-payslips")
def get_my_payslips(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp_id = get_current_employee_id(current_user)
    return PayrollService.get_payslips(db, employee_id=emp_id, is_published=True, skip=skip, limit=limit)


# =============================================================================
# Statutory Configuration
# =============================================================================
@router.get("/statutory-configs", response_model=List[StatutoryConfigurationResponse])
def get_statutory_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_hr_or_admin(current_user)
    return PayrollService.get_statutory_configs(db)


@router.put("/statutory-configs/{config_id}", response_model=StatutoryConfigurationResponse)
def update_statutory_config(
    config_id: int,
    data: StatutoryConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role or current_user.role.name.lower() != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can update statutory rules.")
    return PayrollService.update_statutory_config(db, config_id, data, user_id=current_user.id)
